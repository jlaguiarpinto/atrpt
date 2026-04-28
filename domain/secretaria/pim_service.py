#atrpt/domain/secretaria/pim_service.py
import fitz
import re
import pandas as pd
import logging
from domain.secretaria.pim_context import PimContext
from domain.shared.strings import limpar_string, simplificar_nome
from infrastructure.file_system.io import guardar_df, ler_excel
from infrastructure.persistence.secretaria.pim_repository import PimRepository as PimRepo
from infrastructure.persistence.residentes_repository import ResidentesRepository as ResidentesRepo
from infrastructure.persistence.contacorrente_repository import ContaCorrenteRepository as CCRepo

class Pim:

    def __init__(
        self,
        ctx: PimContext,
        residentes_repo,
        conta_corrente_repo,
        pim_repo
    ):
        self.ctx = ctx

        self.residentes_repo = residentes_repo
        self.conta_corrente_repo = conta_corrente_repo
        self.pim_repo = pim_repo

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
        csag = pd.read_excel(ctx.csag_file,skiprows=1)
        csag = csag.dropna(axis=1, how="all")
        csag=self.normalizar_colunas(csag)
        idx_total = csag[csag.iloc[:,0].astype(str).str.contains("TOTAL", na=False)].index
        if len(idx_total):
            csag = csag.loc[:idx_total[0]-1]
        csag["total"] = (
            csag["faturas_s_protocolo_desconto"].fillna(0)
            + csag["faturas_c_protocolo_desconto"].fillna(0)
        )
        self.csag=csag[["no_cliente","no_fatura","nome_utente","total"]]
        self.csag_clientes = (
            csag.groupby("no_cliente")
                .agg(total_csag=("total","sum"))
                .reset_index()
                .rename(columns={"no_cliente":"ncli"})
        )
      
    def _split_nfat(self,valor):
        if pd.isna(valor):
            return None, None
        s = str(valor).strip()
        # separar prefixo e número final
        m = re.match(r"(.*?)(\d+)$", s)
        if m:
            prefixo = m.group(1).strip()
            numero = m.group(2).strip()
            return prefixo if prefixo else None, numero

        return None, s  # fallback
    
    def comparar_csag(self):
        self.faturas["ncli"] = self.faturas["ncli"].astype(str)
        self.faturas["nfat"] = self.faturas["nfat"].astype(str)
        self.csag = self.csag.rename(columns={"no_cliente": "ncli","no_fatura":"nfat"})
        self.csag["ncli"] = self.csag["ncli"].astype(str).str.strip()
        self.csag["nfat"] = self.csag["nfat"].astype(str).str.strip()
        self.csag[["nfat_doc", "nfat"]] = self.csag["nfat"].apply(self._split_nfat).apply(pd.Series)
        comp = self.faturas.merge(
            self.csag,
            on=["nfat"],
            how="outer", suffixes=("_pdf", "_csag"))

        diferencas = comp[comp["total_pdf"].round(2) != comp["total_csag"].round(2)]
        guardar_df(diferencas, self.ctx.diferencas_file)

        return (diferencas)
          
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
        breakpoint()
        # guardar
        self.pim_repo.salvar_pim(pim_final)     
        guardar_df(df,self.ctx.faturacao_residentes_file)

        return pim_final

