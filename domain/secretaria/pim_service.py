#atrpt/domain/secretaria/pim_service.py
import fitz
import re
import pandas as pd
from domain.secretaria.pim_context import PimContext
from domain.shared.strings import limpar_string, simplificar_nome, normalizar_colunas
from infrastructure.file_system.io import guardar_df, ler_excel
from infrastructure.persistence.secretaria.pim_repository import PimRepository as PimRepo
from infrastructure.persistence.secretaria.residentes_repository import ResidentesRepository as ResidentesRepo
from infrastructure.persistence.secretaria.contacorrente_repository import ContaCorrenteRepository as CCRepo

class Pim:

    def __init__(
        self,
        ctx: PimContext,
        residentes_repo,
        conta_corrente_repo,
        pim_repo,
        csag_repo=None,
    ):
        self.ctx = ctx

        self.residentes_repo = residentes_repo
        self.conta_corrente_repo = conta_corrente_repo
        self.pim_repo = pim_repo
        self.csag_repo = csag_repo

        self.residentes = pd.DataFrame(residentes_repo.get_all())
        self.cc = pd.DataFrame(conta_corrente_repo.get_all())

    def ler_faturas_pdf(self):

        pasta = self.ctx.pim_mensal_dir

        if not pasta.exists():
            raise FileNotFoundError(f"Diretório inexistente: {pasta}")

        pdfs = sorted(pasta.glob("*.pdf"))
        if not pdfs:
            raise RuntimeError("Nenhum PDF encontrado no diretório PIM mensal.")
        registos = []
        for pdf_path in pdfs:
            faturas_pdf = self._extrair_inf_de_pdf(pdf_path)
            if not faturas_pdf:                                     continue
            registos.extend(faturas_pdf)
        self.faturas = pd.DataFrame.from_records(registos)
        guardar_df(self.faturas,self.ctx.pdf_faturas)   
        return self.faturas

    def _obter_linhas_pdf(self,doc):
        linhas_pdf = []
        for page_num, page in enumerate(doc):
            blocos = page.get_text("dict")['blocks']
            blocos_linha = sorted(
                [b for b in blocos if "lines" in b],
                key=lambda b: b["bbox"][1]
            )
            for b in blocos_linha:
                texto = " ".join(span["text"] for line in b["lines"] for span in line["spans"])
                linhas_pdf.append((page_num, texto.strip()))
        return linhas_pdf

    def _extrair_inf_de_pdf(self,pdf):

        """
        Extrai faturas ou notas de crédito a partir de um PDF da farmácia.
        Cada documento inicia-se com 'Original Fatura' ou 'Original Nota de Crédito'.
        O campo 'n.º: FT|NC ...' que poderá estar na linha seguinte.
        São extraídos os campos obrigatórios: Nº Fatura, Nº Cliente, NIF (do cliente) e total a pagar.
        Todos os documentos do PDF devem ter o mesmo Nº Cliente e mesmo NIF.
        A leitura de uma fatura considera-se concluída ao encontrar o total a pagar.
        Linhas seguintes (mesmo noutra página) que não tenham nova fatura são ignoradas,
        salvo se começarem um novo documento com cabeçalho.
        """
        try:
            doc = fitz.open(pdf)
            linhas_pdf = self._obter_linhas_pdf(doc)
            faturas = self._parse_linhas_pdf(linhas_pdf,pdf)
        except Exception as e:
            raise RuntimeError(f"Erro ao processar o PDF '{pdf}':\n{e}")
        return faturas

    def _extrair_numero_fatura(self, linhas_pdf, idx):

        # garantir que existe linha seguinte
        if idx + 1 >= len(linhas_pdf):
            return None

        linha = linhas_pdf[idx + 1][1]

        m = re.search(
            r'n[ºo.]*[:\s]+(FT|NC)\s+([A-Z0-9]+/\d+)',
            linha,
            re.IGNORECASE
        )

        if not m:
            return None

        _, num_raw = m.groups()

        # exemplo: FT A/12345
        if "/" in num_raw:
            return num_raw.split("/")[-1]

        return num_raw

    def _parse_linhas_pdf(self, linhas_pdf, pdf):
        import logging

        faturas = []
        fatura = None
        n_fat_atual = None

        for i, (_, linha) in enumerate(linhas_pdf):

            # ------------------------------------------------
            # detetar início de nova fatura
            # ------------------------------------------------
            if "Original Fatura" in linha or "Original Nota de Crédito" in linha:

                fat_num = self._extrair_numero_fatura(linhas_pdf, i)

                if fat_num and fat_num != n_fat_atual:

                    if fatura and fatura.get("total") is not None:
                        faturas.append(fatura)

                    fatura = {
                        "nfat": fat_num,
                        "ncli": None,
                        "NIF": None,
                        "total": None,
                        "filename": pdf.name
                    }

                    n_fat_atual = fat_num
                    continue

            if not fatura:
                continue

            # ------------------------------------------------
            # cliente
            # ------------------------------------------------
            if not fatura["ncli"]:
                m = re.search(r'Cliente\s+N[ºo.]*[:\s]*([0-9]{3,})', linha, re.IGNORECASE)
                if m:
                    fatura["ncli"] = limpar_string(m.group(1))

            # ------------------------------------------------
            # NIF
            # ------------------------------------------------
            if fatura["ncli"] and not fatura["NIF"]:

                candidatos = re.findall(r'N[ºo.]*\s*CONT[.:]*\s*(\d{9})', linha, re.IGNORECASE)

                candidatos = [n for n in candidatos if n != '506254496']

                if candidatos:
                    nif = re.sub(r"\D", "", candidatos[0])
                    if len(nif) == 9:
                        fatura["NIF"] = nif

            # ------------------------------------------------
            # total
            # ------------------------------------------------
            if not fatura["total"] and "Total a pagar" in linha:
                m = re.search(r'Total a pagar[^\d\-]{0,10}(-?\d+[.,]\d{2})', linha)

                if m:
                    fatura["total"] = round(
                        float(m.group(1).replace('.', '').replace(',', '.')),
                        2
                    )
        logging.info(f"✅ Faturas extraídas do PDF '{pdf.name}': {len(faturas)}")

        # guardar última
        if fatura and fatura.get("total") is not None:
            faturas.append(fatura)

        return faturas

    def agregar_por_residente(self):
        fat = self.faturas.copy()
        self.residentes_faturacao = fat.groupby("NIF").agg(
          nfaturas=("nfat", "count"),
          total=("total", "sum"),
          filename=("filename", lambda x: list(pd.unique(x)))
            ).reset_index()
        return self.residentes_faturacao
    
    def juntar_dados_residente(self,df):
        self.residentes_faturacao=df.merge(
            self.tabela_nif_residente, on="NIF", how="left"
        )
        self.residentes_faturacao["nome"] = self.residentes_faturacao["nome"].apply(simplificar_nome)
        guardar_df(self.residentes_faturacao,self.ctx.faturacao_residentes_file)
        return self.residentes_faturacao
   
    def construir_tabela_residentes(self):

        df_ex = pd.DataFrame(self.conta_corrente_repo.get_all())
        df_cc = pd.DataFrame(self.conta_corrente_repo.get_all_f3m())
        df_ex["id"] = df_ex["id"].astype("Int64")
        df_cc["id"] = df_cc["id"].astype("Int64")
        df_ex=df_ex[["id","excepcao"]]
        df_cc=df_cc[["id","numero_residente","NIF"]]
        residentes = pd.DataFrame(self.residentes_repo.get_all()
        )
         # manter registo com maior ID por NIF
        df_cc = (
            df_cc.sort_values("id")
                .drop_duplicates("NIF", keep="last")
        )

        # adicionar especial
        base = df_ex.merge(df_cc, on="id", how="left")
        base = base.drop(columns="id")
        tabela = base.merge(
            residentes[
                [
                    "numero_residente",
                    "nome",
                    "email",
                    "genero",
                    "relacao",
                    "petit_nom"
                ]
            ],
            on="numero_residente",
            how="left"
        )

        self.tabela_nif_residente = tabela

    def ler_resumo_csag(self,ctx):
        import logging
        csag = self.csag_repo.ler()
        csag = csag.dropna(axis=1, how="all")
        csag = normalizar_colunas(csag)
        idx_total = csag[csag.iloc[:,0].astype(str).str.contains("TOTAL", na=False)].index
        if len(idx_total):
            csag = csag.loc[:idx_total[0]-1]

        col_s = next((c for c in csag.columns if "s_protocolo" in c), None)
        col_c = next((c for c in csag.columns if "c_protocolo" in c), None)
        if col_s is None:
            logging.warning(f"Coluna S/Protocolo não encontrada. Colunas: {list(csag.columns)}")
        if col_c is None:
            logging.warning(f"Coluna C/Protocolo não encontrada. Colunas: {list(csag.columns)}")

        zeros = pd.Series(0.0, index=csag.index)
        def to_num(col): return pd.to_numeric(csag[col], errors="coerce").fillna(0)
        csag["total"] = (to_num(col_s) if col_s else zeros) + (to_num(col_c) if col_c else zeros)
        self.csag=csag[["no_cliente","no_fatura","nome_utente","total"]]
        self.csag_clientes = (
            csag.groupby("no_cliente")
                .agg(total_csag=("total","sum"))
                .reset_index()
                .rename(columns={"no_cliente":"ncli"})
        )
      
    def _split_nfat(self, val):
        s = str(val).strip()
        if s.upper().startswith("NC"):
            return "NC", s[2:].strip().lstrip("/").strip()
        return "", s

    def comparar_csag(self):
        fat = self.faturas.copy()
        fat["ncli"] = fat["ncli"].astype(str).str.strip()
        fat["nfat"] = fat["nfat"].astype(str).str.strip()

        csag = self.csag.rename(columns={"no_cliente": "ncli", "no_fatura": "nfat"}).copy()
        csag["ncli"] = csag["ncli"].astype(str).str.strip()
        csag["nfat"] = csag["nfat"].astype(str).str.strip()
        csag[["tipo_doc", "nfat"]] = csag["nfat"].apply(self._split_nfat).apply(pd.Series)

        comp = fat.merge(csag, on="nfat", how="outer", suffixes=("_pdf", "_csag"))

        def _classificar(row):
            if pd.isna(row.get("total_pdf")) or row.get("total_pdf") == "":
                return "so_csag"
            if pd.isna(row.get("total_csag")) or row.get("total_csag") == "":
                return "so_pdf"
            difs = []
            if str(row.get("ncli_pdf", "")).strip() != str(row.get("ncli_csag", "")).strip():
                difs.append("ncli")
            if round(float(row["total_pdf"]), 2) != round(float(row["total_csag"]), 2):
                difs.append("total")
            return "+".join(difs) if difs else "ok"

        comp["diferenca"] = comp.apply(_classificar, axis=1)
        diferencas = comp[comp["diferenca"] != "ok"]
        guardar_df(diferencas, self.ctx.diferencas_file)
        return diferencas
          
    def construir_novo_pim(self):

        pim = self.pim_repo.ler_pim()
        pim[["numero_residente", "ncli"]] = pim[["numero_residente", "ncli"]].astype("Int64").astype("string")
        fat = ler_excel(self.ctx.faturacao_residentes_file)
        fat["numero_residente"] = fat["numero_residente"].astype("Int64").astype("string")
        pim["anterior"] = pim["saldo"]                                                  # saldo anterior
        df = pim.merge(fat,on="numero_residente",how="outer",suffixes=("", "_fat"))     # merge financeiro
        df["nome"] = df["nome_fat"].combine_first(df["nome"])
        df = df.drop(columns="nome_fat")
        df["especial"] = df["especial"].combine_first(df["excepcao"])
        df["atual"] = df["total_fat"].fillna(0)                                         # faturação do mês
        df["anterior"] = df["anterior"].fillna(0)                                       # saldo anterior
        df["total"] = df["anterior"] + df["atual"]                                      # total e saldo
        df["saldo"] = df["total"]
        # campos operacionais
        df["recebido"] = 0
        df["data"] = ""
        df["user"] = ""
        df["data_envio_recibo"] = ""
        # remover residentes sem saldo
        df = df[df["saldo"] != 0]
        # colunas finais do PIM
        pim_final_cols = [
            "numero_residente",
            "ncli",
            "nome",
            "nfat",
            "especial",
            "anterior",
            "atual",
            "total",
            "recebido",
            "saldo",
            "data",
            "user",
            "data_envio_recibo",
        ]
        pim_final = df[pim_final_cols].copy()
        # guardar
        self.pim_repo.salvar_pim(pim_final)     
        guardar_df(df,self.ctx.faturacao_residentes_file)

        return pim_final

