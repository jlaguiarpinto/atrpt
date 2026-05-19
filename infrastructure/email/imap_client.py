# infrastructure/email/imap_client.py
#
# Cliente IMAP usando apenas imaplib (stdlib).
# Lê pastas, lista mensagens e obtém corpo de mensagens.

import email
import email.message
import imaplib
import logging
import re
import ssl as _ssl
from email.header import decode_header as _decode_header

logger = logging.getLogger(__name__)

_FATURA_SUBJ_KW = ("fatura", "factura", "invoice", "nota de cr", "nota cr", "nota de d")
_RECIBO_SUBJ_KW = ("recibo", "receipt")
_URL_RE         = re.compile(r'https?://[^\s<>"\'\)\]\[]+', re.IGNORECASE)
_FATURA_URL_KW  = frozenset(["fatura", "factura", "invoice", "download", "pdf",
                               "document", "billing", "nota"])


def _is_fatura_subj(assunto: str) -> bool:
    s = assunto.lower()
    return (any(k in s for k in _FATURA_SUBJ_KW) and
            not any(k in s for k in _RECIBO_SUBJ_KW))


def _extrair_urls_fatura(corpo: str) -> list[str]:
    urls = []
    for url in _URL_RE.findall(corpo):
        if any(kw in url.lower() for kw in _FATURA_URL_KW):
            urls.append(url.rstrip(".,;:!?)>"))
    return urls


def _decode_str(raw) -> str:
    if raw is None:
        return ""
    parts = _decode_header(raw)
    out = []
    for fragment, charset in parts:
        if isinstance(fragment, bytes):
            try:
                out.append(fragment.decode(charset or "utf-8", errors="replace"))
            except Exception:
                out.append(fragment.decode("latin-1", errors="replace"))
        else:
            out.append(str(fragment))
    return "".join(out)


class ImapClient:

    def __init__(self, host: str, port: int, user: str, password: str, ssl: bool = True):
        self.host     = host
        self.port     = port
        self.user     = user
        self.password = password
        self.ssl      = ssl
        self._conn: imaplib.IMAP4 | None = None

    # ------------------------------------------------------------------
    # Ligação
    # ------------------------------------------------------------------

    def connect(self):
        if self.ssl:
            self._conn = imaplib.IMAP4_SSL(self.host, self.port)
        else:
            self._conn = imaplib.IMAP4(self.host, self.port)
        self._conn.login(self.user, self.password)
        logger.info("IMAP ligado: %s@%s", self.user, self.host)

    def disconnect(self):
        if self._conn:
            try:
                self._conn.logout()
            except Exception:
                pass
            self._conn = None

    def _reconnect(self):
        try:
            self.disconnect()
        except Exception:
            pass
        self.connect()
        logger.warning("IMAP reconectado após quebra de ligação")

    def _run(self, func):
        """Executa func(); se a ligação cair, reconecta e tenta uma vez mais."""
        _CONN_ERRORS = (imaplib.IMAP4.abort, imaplib.IMAP4.error, OSError, _ssl.SSLError)
        try:
            return func()
        except _CONN_ERRORS as exc:
            logger.warning("IMAP: ligação perdida (%s), a reconectar…", exc)
            self._reconnect()
            return func()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *_):
        self.disconnect()

    # ------------------------------------------------------------------
    # Pastas
    # ------------------------------------------------------------------

    @property
    def is_connected(self) -> bool:
        return self._conn is not None

    def listar_pastas(self) -> list[str]:
        _, data = self._conn.list()
        pastas = []
        for item in data:
            if not item:
                continue
            decoded = item.decode("utf-8", errors="replace") if isinstance(item, bytes) else str(item)
            # formato: (\Flags) "/" "Nome" ou (\Flags) "/" Nome
            m = re.search(r'"([^"]+)"\s*$', decoded)
            if m:
                pastas.append(m.group(1))
            else:
                parts = decoded.rsplit(None, 1)
                if parts:
                    pastas.append(parts[-1].strip('"'))
        return pastas

    def status_pastas(self) -> list[tuple[str, int]]:
        """Devolve [(nome_pasta, total_mensagens)] para pastas não vazias."""
        pastas = self.listar_pastas()
        resultado = []
        for pasta in pastas:
            try:
                _, data = self._conn.status(f'"{pasta}"', "(MESSAGES)")
                if data and data[0]:
                    raw = data[0] if isinstance(data[0], bytes) else data[0].encode()
                    m = re.search(rb"MESSAGES (\d+)", raw)
                    if m and int(m.group(1)) > 0:
                        resultado.append((pasta, int(m.group(1))))
            except Exception:
                logger.debug("Não foi possível obter status de '%s'", pasta)
        return resultado

    # ------------------------------------------------------------------
    # Cabeçalhos para análise estatística (From + To + Subject)
    # ------------------------------------------------------------------

    def listar_cabecalhos_analise(self, pasta: str, limite: int = 500) -> list[dict]:
        return self._run(lambda: self._listar_cabecalhos_analise_impl(pasta, limite))

    def _listar_cabecalhos_analise_impl(self, pasta: str, limite: int) -> list[dict]:
        self._conn.select(f'"{pasta}"', readonly=True)
        _, data = self._conn.uid("search", None, "ALL")
        uids = data[0].split() if data and data[0] else []
        uids = uids[-limite:]

        if not uids:
            return []

        uid_str = b",".join(uids)
        _, fetch_data = self._conn.uid("fetch", uid_str, "(RFC822.HEADER)")

        result = []
        for item in fetch_data:
            if not isinstance(item, tuple) or len(item) < 2:
                continue
            raw_hdr = item[1]
            if not isinstance(raw_hdr, bytes):
                continue
            msg = email.message_from_bytes(raw_hdr)
            ct = msg.get("Content-Type", "").lower()
            result.append({
                "de":       _decode_str(msg.get("From",    "")),
                "para":     _decode_str(msg.get("To",      "")),
                "assunto":  _decode_str(msg.get("Subject", "")),
                "tem_anexo": "multipart/mixed" in ct,
            })
        return result

    # ------------------------------------------------------------------
    # Emails com anexos PDF (para leitura de faturas)
    # ------------------------------------------------------------------

    def obter_emails_com_pdf(self, pasta: str, limite: int = 200) -> list[dict]:
        return self._run(lambda: self._obter_emails_com_pdf_impl(pasta, limite))

    def _obter_emails_com_pdf_impl(self, pasta: str, limite: int) -> list[dict]:
        self._conn.select(f'"{pasta}"', readonly=True)
        _, data = self._conn.uid("search", None, "ALL")
        uids = data[0].split() if data and data[0] else []
        uids = uids[-limite:]
        if not uids:
            return []

        # Passo 1 — cabeçalhos para filtrar multipart/mixed
        uid_str = b",".join(uids)
        _, hdr_data = self._conn.uid("fetch", uid_str, "(UID RFC822.HEADER)")
        candidatos = []
        uid_meta   = {}
        for item in hdr_data:
            if not isinstance(item, tuple) or len(item) < 2:
                continue
            raw_info, raw_hdr = item[0], item[1]
            if not isinstance(raw_info, bytes) or not isinstance(raw_hdr, bytes):
                continue
            m_uid = re.search(rb"UID (\d+)", raw_info)
            if not m_uid:
                continue
            uid = m_uid.group(1).decode()
            msg = email.message_from_bytes(raw_hdr)
            ct  = msg.get("Content-Type", "").lower()
            uid_meta[uid] = {
                "de":      _decode_str(msg.get("From",    "")),
                "assunto": _decode_str(msg.get("Subject", "(sem assunto)")),
                "data":    msg.get("Date", ""),
            }
            if "mixed" in ct:
                candidatos.append(uid.encode())

        if not candidatos:
            return []

        # Passo 2 — corpo completo só dos candidatos
        uid_str2 = b",".join(candidatos)
        _, body_data = self._conn.uid("fetch", uid_str2, "(UID RFC822)")
        result = []
        for item in body_data:
            if not isinstance(item, tuple) or len(item) < 2:
                continue
            raw_info, raw_body = item[0], item[1]
            if not isinstance(raw_info, bytes) or not isinstance(raw_body, bytes):
                continue
            m_uid = re.search(rb"UID (\d+)", raw_info)
            if not m_uid:
                continue
            uid = m_uid.group(1).decode()
            msg_full = email.message_from_bytes(raw_body)
            pdfs = ImapClient._extrair_pdfs(msg_full)
            if pdfs:
                result.append({
                    "uid":  uid,
                    "pdfs": pdfs,
                    **uid_meta.get(uid, {"de": "", "assunto": "", "data": ""}),
                })
        return result

    @staticmethod
    def _extrair_pdfs(msg: email.message.Message) -> list[dict]:
        pdfs = []
        for part in msg.walk():
            ct = part.get_content_type().lower()
            fn = _decode_str(part.get_filename() or "")
            is_pdf = ct == "application/pdf" or (
                ct in ("application/octet-stream", "application/force-download")
                and fn.lower().endswith(".pdf")
            )
            if not is_pdf:
                continue
            payload = part.get_payload(decode=True)
            if payload:
                pdfs.append({"nome": fn or "fatura.pdf", "dados": payload})
        return pdfs

    # ------------------------------------------------------------------
    # Catalogar emails de fatura numa pasta
    # ------------------------------------------------------------------

    def catalogar_pasta_faturas(self, pasta: str, limite: int = 500,
                                 callback=None) -> dict:
        return self._run(
            lambda: self._catalogar_pasta_faturas_impl(pasta, limite, callback)
        )

    def _catalogar_pasta_faturas_impl(self, pasta: str, limite: int, callback) -> dict:
        self._conn.select(f'"{pasta}"', readonly=True)
        _, data = self._conn.uid("search", None, "ALL")
        uids = data[0].split() if data and data[0] else []
        uids = uids[-limite:]
        if not uids:
            return {"com_pdf": [], "com_link": [], "ignorados": 0, "total": 0}

        total = len(uids)

        # Passo 1 — cabeçalhos para filtrar por assunto
        uid_str = b",".join(uids)
        _, hdr_data = self._conn.uid("fetch", uid_str, "(UID RFC822.HEADER)")

        relevantes = []   # (uid_bytes, meta_dict)
        ignorados  = 0

        for item in hdr_data:
            if not isinstance(item, tuple) or len(item) < 2:
                continue
            raw_info, raw_hdr = item[0], item[1]
            if not isinstance(raw_info, bytes) or not isinstance(raw_hdr, bytes):
                continue
            m_uid = re.search(rb"UID (\d+)", raw_info)
            if not m_uid:
                continue
            uid_b = m_uid.group(1)
            msg = email.message_from_bytes(raw_hdr)
            assunto = _decode_str(msg.get("Subject", ""))
            if not _is_fatura_subj(assunto):
                ignorados += 1
                continue
            relevantes.append((uid_b, {
                "uid":     uid_b.decode(),
                "de":      _decode_str(msg.get("From", "")),
                "assunto": assunto,
                "data":    msg.get("Date", ""),
            }))

        com_pdf  = []
        com_link = []

        if not relevantes:
            return {"com_pdf": com_pdf, "com_link": com_link,
                    "ignorados": ignorados, "total": total}

        # Passo 2 — corpo completo dos emails relevantes (lotes de 20)
        rel_meta = {uid_b.decode(): meta for uid_b, meta in relevantes}
        chunk_size = 20
        rel_uids   = [uid_b for uid_b, _ in relevantes]

        for start in range(0, len(rel_uids), chunk_size):
            chunk = rel_uids[start:start + chunk_size]
            _, body_data = self._conn.uid("fetch", b",".join(chunk), "(UID RFC822)")

            for item in body_data:
                if not isinstance(item, tuple) or len(item) < 2:
                    continue
                raw_info, raw_body = item[0], item[1]
                if not isinstance(raw_info, bytes) or not isinstance(raw_body, bytes):
                    continue
                m_uid = re.search(rb"UID (\d+)", raw_info)
                if not m_uid:
                    continue
                uid_s = m_uid.group(1).decode()
                meta  = rel_meta.get(uid_s, {})
                msg_full = email.message_from_bytes(raw_body)

                pdfs = []
                for part in msg_full.walk():
                    ct      = part.get_content_type().lower()
                    fn      = _decode_str(part.get_filename() or "")
                    is_pdf  = ct == "application/pdf" or fn.lower().endswith(".pdf")
                    if not is_pdf:
                        continue
                    payload = part.get_payload(decode=True)
                    if payload:
                        pdfs.append({"nome": fn or "fatura.pdf", "dados": payload})

                if pdfs:
                    com_pdf.append({**meta, "pdfs": pdfs})
                else:
                    corpo = ImapClient._extrair_corpo(msg_full)
                    urls  = _extrair_urls_fatura(corpo)
                    if urls:
                        com_link.append({**meta, "urls": urls})

            if callback:
                callback(min(start + chunk_size, len(rel_uids)), len(rel_uids))

        return {"com_pdf": com_pdf, "com_link": com_link,
                "ignorados": ignorados, "total": total}

    # ------------------------------------------------------------------
    # Lista de mensagens (apenas cabeçalhos)
    # ------------------------------------------------------------------

    def listar_mensagens(self, pasta: str, limite: int = 200) -> list[dict]:
        return self._run(lambda: self._listar_mensagens_impl(pasta, limite))

    def _listar_mensagens_impl(self, pasta: str, limite: int) -> list[dict]:
        self._conn.select(f'"{pasta}"', readonly=True)
        _, data = self._conn.uid("search", None, "ALL")
        uids = data[0].split() if data and data[0] else []
        uids = uids[-limite:]   # mais recentes (estão no fim)

        if not uids:
            return []

        uid_str = b",".join(uids)
        _, fetch_data = self._conn.uid("fetch", uid_str, "(UID FLAGS RFC822.HEADER)")

        msgs = []
        for item in fetch_data:
            if not isinstance(item, tuple) or len(item) < 2:
                continue
            raw_info, raw_hdr = item[0], item[1]
            if not isinstance(raw_info, bytes) or not isinstance(raw_hdr, bytes):
                continue

            m_uid   = re.search(rb"UID (\d+)", raw_info)
            m_flags = re.search(rb"FLAGS \(([^)]*)\)", raw_info)
            uid   = m_uid.group(1).decode()   if m_uid   else "?"
            flags = m_flags.group(1).decode() if m_flags else ""
            seen  = r"\Seen" in flags

            msg = email.message_from_bytes(raw_hdr)
            msgs.append({
                "uid":     uid,
                "de":      _decode_str(msg.get("From",    "")),
                "assunto": _decode_str(msg.get("Subject", "(sem assunto)")),
                "data":    msg.get("Date", ""),
                "lida":    seen,
            })

        return list(reversed(msgs))  # mais recente primeiro

    # ------------------------------------------------------------------
    # Corpo de uma mensagem
    # ------------------------------------------------------------------

    def obter_mensagem(self, pasta: str, uid: str) -> dict:
        return self._run(lambda: self._obter_mensagem_impl(pasta, uid))

    def _obter_mensagem_impl(self, pasta: str, uid: str) -> dict:
        self._conn.select(f'"{pasta}"', readonly=True)
        _, data = self._conn.uid("fetch", uid, "(RFC822)")
        raw = b""
        if data and isinstance(data[0], tuple) and len(data[0]) >= 2:
            raw = data[0][1]

        msg = email.message_from_bytes(raw)
        corpo = self._extrair_corpo(msg)
        return {
            "uid":     uid,
            "de":      _decode_str(msg.get("From",    "")),
            "para":    _decode_str(msg.get("To",      "")),
            "assunto": _decode_str(msg.get("Subject", "")),
            "data":    msg.get("Date", ""),
            "corpo":   corpo,
        }

    # ------------------------------------------------------------------
    # Helpers de decodificação
    # ------------------------------------------------------------------

    @staticmethod
    def _extrair_corpo(msg: email.message.Message) -> str:
        plain = html = None
        if msg.is_multipart():
            for part in msg.walk():
                ct = part.get_content_type()
                if "attachment" in part.get("Content-Disposition", ""):
                    continue
                if ct == "text/plain" and plain is None:
                    plain = ImapClient._decode_part(part)
                elif ct == "text/html" and html is None:
                    html = ImapClient._decode_part(part)
        else:
            ct = msg.get_content_type()
            if ct == "text/plain":
                plain = ImapClient._decode_part(msg)
            elif ct == "text/html":
                html = ImapClient._decode_part(msg)

        if plain:
            return plain
        if html:
            return ImapClient._strip_html(html)
        return "(sem corpo)"

    @staticmethod
    def _decode_part(part: email.message.Message) -> str:
        payload = part.get_payload(decode=True)
        if not payload:
            return ""
        charset = part.get_content_charset() or "utf-8"
        try:
            return payload.decode(charset, errors="replace")
        except Exception:
            return payload.decode("latin-1", errors="replace")

    @staticmethod
    def _strip_html(html: str) -> str:
        text = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", "", text)
        text = text.replace("&nbsp;", " ").replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
