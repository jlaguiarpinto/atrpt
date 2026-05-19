# application/secretaria/atualizar_residentes_cc_usecase.py
#
# Actualiza a tabela residentes_cc (SQLite) a partir de três fontes externas:
#
#   1. Residentes_F3M.xlsx  → atual (= F3M Saldo), mensalidade (= F3M Total),
#      activo, numero_socio, nif, data_nascimento, data_admissao, data_fim
#      chave: CodigoUtente = numero_residente
#
#   2. pim_corrente (SQLite, ciclo activo) ou pim_historico (fallback, período mais recente)
#      → pim (= saldo líquido PIM após recebimentos), anterior (= saldo do período anterior)
#      chave: numero_residente
#
#   3. F3M_Associados_saldos.xlsx  → quota (= coluna H)
#      cadeia: coluna A (Numero = F3M ID) → Residentes_F3M.ID → CodigoUtente → numero_residente
#
# Actualiza residentes_cc (colunas dinâmicas) e sincroniza residentes com campos
# vindos do F3M (numero_socio, nif, datas). Conflitos em numero_socio e nif são
# reportados mas não sobrescritos.

import logging
import sqlite3

import pandas as pd

logger = logging.getLogger(__name__)


_SQL_PIM_CORRENTE = """
    SELECT numero_residente,
           saldo     AS pim,
           anterior,
           saldo
    FROM pim_corrente
"""

_SQL_PIM_HISTORICO_RECENTE = """
    SELECT numero_residente,
           saldo     AS pim,
           anterior,
           saldo
    FROM pim_historico
    WHERE (ano * 100 + mes) = (
        SELECT MAX(p2.ano * 100 + p2.mes)
        FROM pim_historico p2
        WHERE p2.numero_residente = pim_historico.numero_residente
    )
"""


class AtualizarResidentesCCUseCase:

    def __init__(self, db_path: str, f3m_path: str, quotas_path: str):
        self.db_path     = str(db_path)
        self.f3m_path    = str(f3m_path)
        self.quotas_path = str(quotas_path)

    def execute(self) -> dict:
        """
        Actualiza residentes_cc com os valores mais recentes das três fontes.
        Sincroniza residentes com número de sócio, NIF e datas vindos do F3M.
        Devolve {"atualizados": n, "sem_pim": k, "sem_quota": m, "conflitos": [...]}.
        """
        df_f3m   = self._ler_f3m()
        df_pim   = self._ler_pim_historico()
        df_quota = self._ler_quotas(df_f3m)

        # base: residentes que já existem em residentes_cc (inner join com o F3M)
        with sqlite3.connect(self.db_path) as conn:
            existentes = pd.read_sql(
                "SELECT numero_residente FROM residentes_cc", conn
            )["numero_residente"].tolist()

        df = df_f3m[df_f3m["numero_residente"].notna()].copy()
        df["numero_residente"] = (
            pd.to_numeric(df["numero_residente"], errors="coerce").astype("Int64")
        )
        df = df[df["numero_residente"].isin(existentes)].copy()

        # junta PIM
        df = df.merge(df_pim, on="numero_residente", how="left")
        sem_pim = int(df["pim"].isna().sum())

        # junta quota
        df = df.merge(df_quota, on="numero_residente", how="left")
        sem_quota = int(df["quota"].isna().sum())

        # seleccionar só as colunas dinâmicas para o UPSERT parcial
        cols_update = ["numero_residente", "atual", "mensalidade", "pim", "saldo", "anterior", "quota", "activo"]
        df_update = df[[c for c in cols_update if c in df.columns]].copy()

        atualizados = self._upsert_parcial(df_update)

        # sincronizar campos do F3M para a tabela residentes
        conflitos = self._sincronizar_residentes(df_f3m)

        logger.info(
            "residentes_cc atualizado: %d registos | sem_pim=%d | sem_quota=%d | conflitos=%d",
            atualizados, sem_pim, sem_quota, len(conflitos),
        )
        return {
            "atualizados": atualizados,
            "sem_pim":     sem_pim,
            "sem_quota":   sem_quota,
            "conflitos":   conflitos,
        }

    # ------------------------------------------------------------------
    # Fontes
    # ------------------------------------------------------------------

    # Mapeamento: nome normalizado (após normalizar_colunas) → campo interno
    # Lista de candidatos por ordem de preferência para cobrir variações de nome no F3M
    _F3M_MAP = {
        "id_f3m":          ["id"],
        "mensalidade":     ["total"],
        "atual":           ["saldo"],
        "numero_residente":["codigoutente"],
        "activo":          ["activo"],
        "numero_socio":    ["numerosocio", "numsocio", "num_socio", "numerosocio"],
        "nif":             ["contribuinte", "nif"],
        "data_nascimento": ["datanascimento", "data_nascimento"],
        "data_admissao":   ["dataadmissao", "data_admissao", "dataentrada", "data_entrada"],
        "data_fim":        ["datafim", "data_fim", "datasaida", "data_saida"],
    }

    def _ler_f3m(self) -> pd.DataFrame:
        from domain.shared.strings import normalizar_colunas
        df = pd.read_excel(self.f3m_path, engine="openpyxl")
        df = normalizar_colunas(df)

        # renomear colunas usando os candidatos definidos em _F3M_MAP
        rename = {}
        for destino, candidatos in self._F3M_MAP.items():
            for cand in candidatos:
                if cand in df.columns and cand not in rename:
                    rename[cand] = destino
                    break
        df = df.rename(columns=rename)

        df["numero_residente"] = pd.to_numeric(df["numero_residente"], errors="coerce")
        df["mensalidade"]      = pd.to_numeric(df["mensalidade"],      errors="coerce").round(2)
        df["atual"]            = pd.to_numeric(df["atual"],            errors="coerce").round(2)
        df["id_f3m"]           = pd.to_numeric(df["id_f3m"],          errors="coerce")
        if "activo" in df.columns:
            df["activo"] = df["activo"].astype(str).str.strip()
        if "numero_socio" in df.columns:
            df["numero_socio"] = pd.to_numeric(df["numero_socio"], errors="coerce")
        if "nif" in df.columns:
            # NIF é numérico no Excel (int ou float); converter para string sem ".0"
            df["nif"] = (
                pd.to_numeric(df["nif"], errors="coerce")
                .apply(lambda x: str(int(x)) if pd.notna(x) else None)
            )
        for col in ("data_nascimento", "data_admissao", "data_fim"):
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip().replace({"nan": None, "NaT": None, "": None})

        keep = ["id_f3m", "numero_residente", "mensalidade", "atual"]
        for col in ("activo", "numero_socio", "nif", "data_nascimento", "data_admissao", "data_fim"):
            if col in df.columns:
                keep.append(col)
        return df[keep]

    def _ler_pim_historico(self) -> pd.DataFrame:
        """Lê dados de PIM para residentes_cc.
        Fonte primária: pim_corrente (dados do ciclo activo).
        Fallback: pim_historico (período mais recente arquivado).
        """
        _empty = pd.DataFrame(columns=["numero_residente", "pim", "saldo", "anterior"])
        try:
            with sqlite3.connect(self.db_path) as conn:
                # preferir pim_corrente se tiver dados
                corrente_count = conn.execute(
                    "SELECT COUNT(*) FROM pim_corrente"
                ).fetchone()[0]
                if corrente_count > 0:
                    df = pd.read_sql(_SQL_PIM_CORRENTE, conn)
                    logger.info("residentes_cc: PIM lido de pim_corrente (%d linhas).", len(df))
                else:
                    # fallback para pim_historico
                    cols_bd = {r[1] for r in conn.execute(
                        "PRAGMA table_info(pim_historico)"
                    ).fetchall()}
                    if not cols_bd:
                        return _empty
                    if "anterior" not in cols_bd:
                        conn.execute("ALTER TABLE pim_historico ADD COLUMN anterior REAL")
                        logger.info("pim_historico: coluna 'anterior' adicionada (migração).")
                    df = pd.read_sql(_SQL_PIM_HISTORICO_RECENTE, conn)
                    logger.info("residentes_cc: PIM lido de pim_historico (%d linhas).", len(df))
        except Exception as e:
            logger.warning("Erro ao ler PIM: %s", e)
            return _empty
        df["numero_residente"] = pd.to_numeric(df["numero_residente"], errors="coerce")
        for col in ("pim", "saldo", "anterior"):
            df[col] = pd.to_numeric(df[col], errors="coerce").round(2)
        return df[["numero_residente", "pim", "saldo", "anterior"]]

    # Campos sincronizados para residentes; os marcados com True geram conflito se divergirem
    _SYNC_FIELDS = {
        "numero_socio":    True,
        "nif":             True,
        "data_nascimento": False,
        "data_admissao":   False,
        "data_fim":        False,
    }

    def _sincronizar_residentes(self, df_f3m: pd.DataFrame) -> list[dict]:
        """
        Actualiza a tabela residentes com campos vindos do F3M.
        - Se o campo está vazio em SQLite → actualiza silenciosamente.
        - Se difere e está marcado como conflito → regista sem sobrescrever.
        - Para datas: actualiza sempre (F3M é fonte de verdade).
        Devolve lista de conflitos [{numero_residente, campo, valor_local, valor_f3m}].
        """
        sync_cols = [c for c in self._SYNC_FIELDS if c in df_f3m.columns]
        if not sync_cols:
            return []

        conflitos = []
        with sqlite3.connect(self.db_path) as conn:
            cols_bd = {r[1] for r in conn.execute("PRAGMA table_info(residentes)").fetchall()}
            sync_cols = [c for c in sync_cols if c in cols_bd]
            if not sync_cols:
                return []

            for _, row in df_f3m[["numero_residente"] + sync_cols].iterrows():
                nr = row.get("numero_residente")
                try:
                    nr = int(nr)
                except (TypeError, ValueError):
                    continue

                cur = conn.execute(
                    f"SELECT {', '.join(sync_cols)} FROM residentes WHERE numero_residente = ?",
                    (nr,),
                )
                stored_row = cur.fetchone()
                if stored_row is None:
                    continue

                stored = dict(zip(sync_cols, stored_row))
                updates = {}

                for campo in sync_cols:
                    f3m_val = row.get(campo)
                    try:
                        if pd.isna(f3m_val):
                            f3m_val = None
                    except TypeError:
                        pass
                    if f3m_val is None:
                        continue
                    f3m_str = str(f3m_val).strip()
                    if not f3m_str or f3m_str.lower() in ("nan", "none", "nat"):
                        continue

                    stored_val = stored.get(campo)
                    stored_str = str(stored_val).strip() if stored_val is not None else ""

                    gera_conflito = self._SYNC_FIELDS[campo]

                    if not stored_str:
                        updates[campo] = f3m_str
                    elif stored_str != f3m_str:
                        if gera_conflito:
                            conflitos.append({
                                "numero_residente": nr,
                                "campo":            campo,
                                "valor_local":      stored_str,
                                "valor_f3m":        f3m_str,
                            })
                        else:
                            # datas: F3M é fonte de verdade, actualizar sempre
                            updates[campo] = f3m_str

                if updates:
                    sets = ", ".join(f"{c} = ?" for c in updates)
                    conn.execute(
                        f"UPDATE residentes SET {sets}, atualizado_em = CURRENT_TIMESTAMP "
                        f"WHERE numero_residente = ?",
                        (*updates.values(), nr),
                    )

        if conflitos:
            logger.warning(
                "Conflitos F3M ↔ SQLite (%d): %s",
                len(conflitos),
                "; ".join(
                    f"nr={c['numero_residente']} {c['campo']}={c['valor_local']!r}≠{c['valor_f3m']!r}"
                    for c in conflitos
                ),
            )
        return conflitos

    def _ler_quotas(self, df_f3m: pd.DataFrame) -> pd.DataFrame:
        """
        Lê F3M_Associados_saldos.xlsx, extrai coluna A (Numero = F3M ID) e
        coluna ValorQuota, e resolve para numero_residente via df_f3m.
        """
        _empty = pd.DataFrame(columns=["numero_residente", "quota"])
        try:
            df_raw = pd.read_excel(self.quotas_path, header=0, engine="openpyxl")
        except Exception as e:
            logger.warning("Não foi possível ler ficheiro de quotas: %s", e)
            return _empty

        # coluna de ID: sempre a primeira coluna (A)
        col_id = df_raw.columns[0]

        # coluna de quota: preferir 'ValorQuota' pelo nome; fallback para índice 11
        if "ValorQuota" in df_raw.columns:
            col_quota = "ValorQuota"
        elif df_raw.shape[1] >= 12:
            col_quota = df_raw.columns[11]
        else:
            logger.warning(
                "quotas: coluna ValorQuota não encontrada e ficheiro tem só %d colunas",
                df_raw.shape[1],
            )
            return _empty

        df_q = pd.DataFrame({
            "id_f3m": pd.to_numeric(df_raw[col_id],    errors="coerce"),
            "quota":  pd.to_numeric(df_raw[col_quota], errors="coerce").round(2),
        }).dropna(subset=["id_f3m"])

        # resolver id_f3m → numero_residente
        mapa = df_f3m[["id_f3m", "numero_residente"]].dropna()
        df_q = df_q.merge(mapa, on="id_f3m", how="inner")
        return df_q[["numero_residente", "quota"]].copy()

    # ------------------------------------------------------------------
    # Persistência
    # ------------------------------------------------------------------

    def _upsert_parcial(self, df: pd.DataFrame) -> int:
        """
        UPDATE apenas das colunas dinâmicas para os residentes já existentes em
        residentes_cc. Não insere novos registos (os inativos históricos do F3M
        não devem ser adicionados à tabela operacional).
        """
        _TEXT_COLS = {"activo"}
        cols_update = [c for c in ["atual", "mensalidade", "pim", "saldo", "anterior", "quota", "activo"]
                       if c in df.columns]
        sets = ", ".join(f"{c} = ?" for c in cols_update)
        sql  = (
            f"UPDATE residentes_cc SET {sets}, atualizado_em = CURRENT_TIMESTAMP "
            f"WHERE numero_residente = ?"
        )
        count = 0
        with sqlite3.connect(self.db_path) as conn:
            for _, row in df.iterrows():
                vals = []
                for c in cols_update:
                    v = row.get(c)
                    try:
                        if pd.isna(v):
                            v = None
                    except TypeError:
                        pass
                    if v is not None:
                        if c in _TEXT_COLS:
                            v = str(v).strip() or None
                        else:
                            try:
                                v = round(float(v), 2)
                            except (TypeError, ValueError):
                                v = None
                    vals.append(v)
                nr = row.get("numero_residente")
                try:
                    nr = int(nr)
                except (TypeError, ValueError):
                    continue
                vals.append(nr)
                cur = conn.execute(sql, tuple(vals))
                count += cur.rowcount
        return count
