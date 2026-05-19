#atrpt/domain/secretaria/pim_service.py
import fitz
import re
import pandas as pd
from domain.secretaria.pim_context import PimContext
from domain.shared.strings import limpar_string, simplificar_nome, normalizar_colunas
from infrastructure.file_system.io import guardar_df, ler_excel

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
        import logging

        pasta = self.ctx.pim_mensal_dir

        if not pasta.exists():
            raise FileNotFoundError(f"Diretório inexistente: {pasta}")

        pdfs = sorted(pasta.glob("*.pdf"))
        if not pdfs:
            raise RuntimeError("Nenhum PDF encontrado no diretório PIM mensal.")

        logging.info(f"Encontrados {len(pdfs)} PDF(s) em '{pasta.name}'.")
        registos = []
        for i, pdf_path in enumerate(pdfs, 1):
            logging.info(f"[{i}/{len(pdfs)}] A processar: {pdf_path.name}")
            faturas_pdf = self._extrair_inf_de_pdf(pdf_path)
            if not faturas_pdf:
                logging.info(f"  → sem faturas.")
                continue
            registos.extend(faturas_pdf)

        self.faturas = pd.DataFrame.from_records(registos)
        logging.info(f"Total extraído: {len(self.faturas)} fatura(s).")
        guardar_df(self.faturas, self.ctx.pdf_faturas)
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
                    fatura["total"] = round(float(m.group(1).replace('.', '').replace(',', '.')),2)
        # guardar última
        if fatura and fatura.get("total") is not None:
            faturas.append(fatura)
        logging.info(f"✅ Faturas extraídas do PDF '{pdf.name}': {len(faturas)}")

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
        return self.csag
      
    def _split_nfat(self, val):
        s = str(val).strip()
        if s.upper().startswith("NC"):
            return "NC", s[2:].strip().lstrip("/").strip()
        return "", s

    def comparar_csag(self):
        # Prepara os dados
        self.faturas["ncli"] = self.faturas["ncli"].astype(str).str.strip()
        self.faturas["nfat"] = self.faturas["nfat"].astype(str).str.strip()
        self.faturas["total"] = self.faturas["total"].round(2)
        
        self.csag = self.csag.rename(columns={"no_cliente": "ncli", "no_fatura": "nfat"})
        self.csag["ncli"] = self.csag["ncli"].astype(str).str.strip()
        self.csag["nfat"] = self.csag["nfat"].astype(str).str.strip()
        self.csag[["nfat_doc", "nfat"]] = self.csag["nfat"].apply(self._split_nfat).apply(pd.Series)
        self.csag["total"] = self.csag["total"].round(2)
        
        lista_diferencas = []
        
        # 1. Divergência de total (mesmo nfat e ncli) - apenas linha do FAT
        diff_total = self.faturas.merge(
            self.csag,
            on=["nfat", "ncli"],
            how="inner",
            suffixes=("", "_csag")
        )
        diff_total = diff_total[diff_total["total"] != diff_total["total_csag"]].copy()
        if not diff_total.empty:
            diff_total["diferenca"] = "total"
            diff_total["nfat_doc"] = ""
            diff_total["ncli_csag"] = diff_total["ncli"]
            lista_diferencas.append(diff_total)
        
        # 2. Divergência de ncli (mesmo nfat e total) - apenas linha do FAT
        diff_ncli = self.faturas.merge(
            self.csag,
            on=["nfat", "total"],
            how="inner",
            suffixes=("", "_csag")
        )
        diff_ncli = diff_ncli[diff_ncli["ncli"] != diff_ncli["ncli_csag"]].copy()
        if not diff_ncli.empty:
            diff_ncli["diferenca"] = "ncli"
            diff_ncli["nfat_doc"] = diff_ncli["nfat"]
            diff_ncli["total_csag"] = diff_ncli["total"]
            lista_diferencas.append(diff_ncli)
        
        # 3. Divergência de nfat (mesmo ncli e total) - apenas linha do FAT
        diff_nfat = self.faturas.merge(
            self.csag,
            on=["ncli", "total"],
            how="inner",
            suffixes=("", "_csag")
        )
        diff_nfat = diff_nfat[diff_nfat["nfat"] != diff_nfat["nfat_csag"]].copy()
        if not diff_nfat.empty:
            diff_nfat["diferenca"] = "nfat"
            diff_nfat["nfat_doc"] = diff_nfat["nfat_csag"]
            diff_nfat["total_csag"] = diff_nfat["total"]
            diff_nfat["ncli_csag"] = diff_nfat["ncli"]
            lista_diferencas.append(diff_nfat)
        
        # 4. Registros apenas no FAT (não existe correspondência em nenhum campo)
        # Precisa excluir os que já foram capturados nas divergências acima
        chaves_com_divergencia = set()
        for df in lista_diferencas:
            chaves_com_divergencia.update(df["nfat"].astype(str) + "|" + df["ncli"].astype(str))
        
        apenas_fat = self.faturas.merge(
            self.csag,
            on=["nfat", "ncli", "total"],
            how="left",
            indicator=True
        )
        apenas_fat = apenas_fat[apenas_fat["_merge"] == "left_only"].copy()
        
        # Remove os que já estão nas divergências
        chave_fat = apenas_fat["nfat"].astype(str) + "|" + apenas_fat["ncli"].astype(str)
        apenas_fat = apenas_fat[~chave_fat.isin(chaves_com_divergencia)]
        
        if not apenas_fat.empty:
            apenas_fat["diferenca"] = "fat"
            apenas_fat["total_csag"] = ""
            apenas_fat["ncli_csag"] = ""
            apenas_fat["nfat_doc"] = ""
            lista_diferencas.append(apenas_fat)
        
        # 5. Registros apenas no CSAG (não existe no FAT)
        apenas_csag = self.csag.merge(
            self.faturas,
            on=["nfat", "ncli", "total"],
            how="left",
            indicator=True
        )
        apenas_csag = apenas_csag[apenas_csag["_merge"] == "left_only"].copy()
        
        if not apenas_csag.empty:
            apenas_csag["diferenca"] = "csag"
            apenas_csag = apenas_csag.rename(columns={
                "total": "total_csag",
                "ncli": "ncli_csag"
            })
            # Adiciona colunas vazias para compatibilidade
            for col in ["nfat", "ncli", "NIF", "total", "filename", "nome_utente"]:
                if col not in apenas_csag.columns:
                    apenas_csag[col] = ""
            lista_diferencas.append(apenas_csag)
        
        # Combina todas as diferenças
        if lista_diferencas:
            diferencas = pd.concat(lista_diferencas, ignore_index=True, sort=False)
            
            # Remove colunas auxiliares
            if "_merge" in diferencas.columns:
                diferencas = diferencas.drop(columns=["_merge"])
            
            # Define a ordem das colunas
            colunas_ordenadas = [
                "nfat", "ncli", "NIF", "total", "filename", "nome_utente", 
                "nfat_doc", "diferenca", "total_csag", "ncli_csag"
            ]
            
            # Mantém apenas colunas que existem no dataframe
            colunas_finais = [col for col in colunas_ordenadas if col in diferencas.columns]
            diferencas = diferencas[colunas_finais]
            
            # Ordena por tipo de diferença
            ordem_diferenca = {"fat": 0, "total": 1, "ncli": 2, "nfat": 3, "csag": 4}
            diferencas["ordem"] = diferencas["diferenca"].map(ordem_diferenca)
            diferencas = diferencas.sort_values("ordem").drop(columns=["ordem"])
        else:
            diferencas = pd.DataFrame()
        
        guardar_df(diferencas, self.ctx.diferencas_file)
        
        return diferencas
          
    _CONTACT_COLS = ["NIF", "email", "genero", "relacao", "petit_nom"]

    def construir_novo_pim(self):
        import logging

        pim = self.pim_repo.ler_pim()
        pim[["numero_residente", "ncli"]] = pim[["numero_residente", "ncli"]].astype("Int64").astype("string")
        fat = ler_excel(self.ctx.faturacao_residentes_file)
        fat["numero_residente"] = fat["numero_residente"].astype("Int64").astype("string")
        pim["anterior"] = pim["saldo"]                                                  # saldo anterior
        # remover colunas que causariam duplicados no merge com suffixes=("", "_fat"):
        # 1) de pim: colunas cujo nome coincidiria com um sufixo gerado por fat
        # 2) de fat: colunas _fat acumuladas de corridas anteriores (o ficheiro é reutilizado)
        fat_cols_orig = list(fat.columns)
        fat_sufixadas = {f"{c}_fat" for c in fat_cols_orig if c != "numero_residente"}
        pim = pim.drop(columns=[c for c in fat_sufixadas if c in pim.columns])
        fat = fat.drop(columns=[c for c in fat_sufixadas if c in fat_cols_orig])
        df = pim.merge(fat, on="numero_residente", how="outer", suffixes=("", "_fat"))  # merge financeiro
        df["nome"] = df["nome_fat"].combine_first(df["nome"])
        df = df.drop(columns="nome_fat", errors="ignore")
        df["especial"] = df["especial"].combine_first(df["excepcao"])
        df["atual"] = df["total_fat"].fillna(0)                                         # faturação do mês
        df["anterior"] = df["anterior"].fillna(0)                                       # saldo anterior
        df["total"] = df["anterior"] + df["atual"]                                      # total e saldo
        df["saldo"] = df["total"]

        # preencher dados de contacto nos saldos transitados sem fatura do mês
        precisa_contacto = any(
            col not in df.columns or df[col].isna().any()
            for col in self._CONTACT_COLS
        )
        if precisa_contacto:
            if not hasattr(self, "tabela_nif_residente"):
                self.construir_tabela_residentes()
            ref = self.tabela_nif_residente[
                ["numero_residente"] + [c for c in self._CONTACT_COLS if c in self.tabela_nif_residente.columns]
            ].copy()
            ref["numero_residente"] = ref["numero_residente"].astype("Int64").astype("string")
            df = df.merge(ref, on="numero_residente", how="left", suffixes=("", "_ref"))
            for col in self._CONTACT_COLS:
                ref_col = f"{col}_ref"
                if ref_col in df.columns:
                    df[col] = df[col].combine_first(df[ref_col]) if col in df.columns else df[ref_col]
                    df = df.drop(columns=ref_col)
            n_transitados = (df["atual"] == 0).sum()
            logging.info(f"{n_transitados} residente(s) com saldo transitado — dados de contacto preenchidos.")

        # campos operacionais
        df["recebido"] = 0
        df["data"] = ""
        df["user"] = ""
        df["data_envio_recibo"] = ""
        # remover residentes sem saldo
        df = df[df["saldo"] != 0]
        # guardar faturacao_residentes com dados de contacto completos
        guardar_df(df, self.ctx.faturacao_residentes_file)
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
        self.pim_repo.salvar_pim(pim_final)
        return pim_final

