# atrpt/application/secretaria/tesouraria_service.py

from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd
import logging

from application.email.email_message import EmailMessage
from application.email.email_sender import EmailSender
from infrastructure.persistence.pim_repository import PimRepository

from domain.shared.strings import remover_acentos, normalizar_nome, simplificar_nome

logger = logging.getLogger(__name__)
class TesourariaService:

    OPCOES_TIPO_MOVIMENTO = {
        1: "mensalidade",
        2: "PIM",
        3: "mensalidade + PIM",
        4: "CentrodeDia", 
        5: "Caução",
        6: "Almoço",
        7: "Quota",
        8: "Financeiro",
        9: "P/ averiguar",
    }

    DESIGNACOES_COMUNS = {
    "trans",
    "transferencia",
    "cxdol",
    }
    
    def __init__(
        self,
        paths: dict,
        emailer,
        residentes_repo,
        conta_corrente_repo,
        comprovativo_repo,
        inflow_repo,
        pim_repo,
        template_builder,
        cfg,
        email_secretaria,
        modo_teste=False,
    ):
        self.paths = paths
        self.emailer = emailer
        self.residentes_repo = residentes_repo
        self.conta_corrente_repo = conta_corrente_repo
        self.comprovativo_repo = comprovativo_repo
        self.inflow_repo = inflow_repo
        self.pim_repo = pim_repo
        self.template_builder=template_builder
        self.email_secretaria=email_secretaria
        self.modo_teste = modo_teste
        self.cfg=cfg
        self.paths_app = self.cfg.paths_app

    def processar_extrato(
        self,
        pedir_input,
        confirmar_adicao,
        validar_callback
    ):
        # -------------------------
        # carregar
        # -------------------------
        self._carregar_dados_iniciais()

        novos = self._filtrar_novos_movimentos(
            self.inflow_diario,
            self.inflow_acumulado
        )
        if novos.empty:
            return {"status": "sem_novos"}

        # -------------------------
        # classificar
        # -------------------------
        df_classificado = self.classificar_movimentos(
            novos,
            pedir_input,
            confirmar_adicao
        )

        # -------------------------
        # validação (UI externa)
        # -------------------------
        df_validado = validar_callback(df_classificado)

        if df_validado is None:
            return {"status": "cancelado"}

        # -------------------------
        # cálculo
        # -------------------------
        df_calculado = self.calcular_distribuicao(df_validado)

        # -------------------------
        # efeitos
        # -------------------------
        self._atualizar_inflow(df_validado)
        self.aplicar_efeitos_financeiros(df_calculado)

        return {
            "status": "ok",
            "novos": len(novos),
            "df": df_calculado
        }

    def _carregar_dados_iniciais(self):
        """Carrega todos os dados necessários para o serviço"""
        self.residentes = self.residentes_repo.get_all()
        self.conta_corrente = self.conta_corrente_repo.get_all()
        self.inflow_diario = self.inflow_repo.ler_extrato_diario()
        self.inflow_acumulado = self.inflow_repo.ler_inflow_acumulado()
        self.pim_df = self.pim_repo.ler_pim()

    def recarregar_dados(self):                # Recarrega todos os dados (útil após atualizações)
        self._carregar_dados_iniciais()

    def atualizar_inflow_acumulado(self, novo_inflow_df: pd.DataFrame) -> pd.DataFrame:
        """
        atualiza o arquivo de inflow acumulado e a referência interna
        """
        self.inflow_repo.salvar_inflow_acumulado(novo_inflow_df)            # Salvar usando o repositório
        self.inflow_acumulado = self.inflow_repo.ler_inflow_acumulado()     # atualizar a referência interna lendo o arquivo atualizado
        return self.inflow_acumulado                                        # Opcional: retornar o valor atualizado

    def substituir_inflow_acumulado(self, novo_inflow_df: pd.DataFrame) -> pd.DataFrame:         # se quiser fazer tudo de uma vez
        """
        Substitui completamente o inflow acumulado e retorna o novo valor
        """
        self.inflow_acumulado = self.inflow_repo.atualizar_e_ler_inflow_acumulado(novo_inflow_df)
        return self.inflow_acumulado

    @staticmethod
    def _filtrar_novos_movimentos(df, acumulado):
        merged = df.merge(acumulado, how="left", indicator=True)
        novos = (merged[merged["_merge"] == "left_only"].drop(columns=["_merge"]))
        return novos

    def classificar_movimentos(self, df, pedir_input, _confirmar_adicao=None):
        df = df.copy()
        df[["numero_residente", "nome", "tipo", "copag"]] = None

        for idx in reversed(df.index):
            data = df.at[idx, "data"]
            valor = float(df.at[idx, "valor"])
            descr = df.at[idx, "descricao"]

            descr = descr if isinstance(descr, str) and descr else ""
            alvo = normalizar_nome(descr) if descr else ""
            v = round(valor, 2)

            numero = self._identificar_residente(data, alvo, v, pedir_input, _confirmar_adicao)
            tipo = None

            if numero:
                residente = self.residentes_repo.get_by_numero(numero)
                df.at[idx, "numero_residente"] = numero
                if residente:
                    df.at[idx, "nome"] = residente.get("nome", "")
                    df.at[idx, "copag"] = residente.get("copag", "")
                tipo = self._classificar_tipo(numero, valor)

            if not tipo and pedir_input:
                menu = "\n".join(f"[{k}] - {v}" for k, v in self.OPCOES_TIPO_MOVIMENTO.items())
                resp = pedir_input(
                    "Tipo Movimento", menu, "int",
                    dados_mov={
                        "data": data, "descricao": descr, "valor": valor,
                        "numero_residente": numero or "",
                        "nome": residente.get("nome", "") if numero and residente else "",
                    }
                )
                tipo = self.OPCOES_TIPO_MOVIMENTO.get(resp)

            df.at[idx, "tipo"] = tipo

        return df

    def _guardar_designacao(self, numero, descricao):
        nova_designacao = remover_acentos(descricao).strip().lower()
        designacoes = ""
        residente = self.residentes_repo.get_by_numero(numero)
        if residente: valor_des = residente.get("saldo")
        if pd.notna(valor_des):
            designacoes = str(valor_des).strip().lower()
            if nova_designacao in designacoes.split(";"):    return
            designacoes += "; "
        designacoes += nova_designacao
        self.residentes_repo.update_designacao(numero, designacoes)

    def _designacao_eh_comum(self, texto: str) -> bool:  #para decidir se a nova designação bancária é salva
        texto = remover_acentos(texto).strip().lower().replace(" ", "")
        tokens = texto.split()
        # Se todos os tokens forem termos comuns → ignorar
        if tokens and all(t in self.DESIGNACOES_COMUNS for t in tokens):
            return True
        return False

    def _identificar_residente(self,data, descricao, valor, pedir_input, _confirmar_adicao=None):
        numero = 0
        TOL = 0.01

        numero = self._encontrar_por_descritivo(descricao)
        if numero == 0:
            numero = self._encontrar_por_valor(valor)
            if numero == 0 and pedir_input:
                numero = pedir_input(
                    "Número Residente",
                    "Indique Número (0 se não residente):",
                    "int",
                    dados_mov={
                        "data": data,
                        "descricao": descricao,
                        "valor": valor,
                        "numero_residente":"",
                        "nome":""
                    }
                ) or 0
            if numero != 0 and _confirmar_adicao and not self._designacao_eh_comum(descricao):
                residente = self.residentes_repo.get_by_numero(numero)
                if residente:
                    confirmar = _confirmar_adicao(
                        numero,
                        residente["nome"],
                        descricao,
                    )
                    if confirmar:
                        self._guardar_designacao(numero, descricao)

        return numero

    def _encontrar_por_descritivo(self, descritivo: str) -> int:
        if not descritivo or not isinstance(descritivo, str):
            return 0
        alvo = normalizar_nome(descritivo)
        df = pd.DataFrame(self.residentes_repo.get_all())
        if df.empty:      return 0
        col = (
            df["designacao_bancaria"]
            .fillna("")
            .str.split(";")
        )

        tmp = df.assign(opcao=col).explode("opcao")
        tmp["opcao"] = tmp["opcao"].apply(normalizar_nome)
        res = tmp.loc[tmp["opcao"] == alvo, "numero_residente"]

        return int(res.iloc[0]) if not res.empty else 0

    def _encontrar_por_valor(self, valor):
        valor = round(float(valor), 2)
        colunas = ['pim', 'atual', 'saldo', 'anterior']
        residentes_cc = self.conta_corrente_repo.get_all()
        df = pd.DataFrame(residentes_cc)
        print(f"valor: {valor}")
        print(df.columns)


        def _match_unico(serie_bool):
            filtro = df[serie_bool]
            if len(filtro) == 1:
                n = filtro['numero_residente'].iloc[0]
                return int(n) if not pd.isna(n) else None
            return None

        for coluna in colunas:
            if coluna not in df.columns:
                continue
            resultado = _match_unico(df[coluna].fillna(0).round(2) == valor)
            if resultado:
                return resultado

        if {'pim', 'anterior'}.issubset(df.columns):
            diferenca = (df['pim'].fillna(0)- df['anterior'].fillna(0)).round(2)
            resultado = _match_unico(diferenca == valor)
            if resultado:
                return resultado
        return 0

    def _classificar_tipo(self, numero, valor):

        if isinstance(numero, int):
            conta = self.conta_corrente_repo.get_by_numero(numero)
        if not conta:
            return ""

        TOL = 0.01
        v = round(float(valor), 2)

        def _val(chave):
            try:
                return round(float(conta.get(chave, 0) or 0), 2)
            except Exception:
                return 0.0
        mensalidade = _val("mensalidade")
        atual = _val("atual")
        pim = _val("pim")
        pim_ant = _val("anterior")
        saldo = _val("saldo")
        if abs(v - atual) < TOL or abs(v - mensalidade) < TOL:
            return "mensalidade"

        if (
            abs(v - pim) < TOL
            or abs(v - pim_ant) < TOL
            or abs(v - (pim - pim_ant)) < TOL
        ):
            return "PIM"

        if abs(v - saldo) < TOL:
            return "mensalidade + PIM"

        return ""

    def _atualizar_inflow(self, inflow_novo):                 #atualiza inflow com os novos movimentos classificados. 

        inflow_novo = inflow_novo.drop('Num_num', axis=1)
        inflow_acumulado = self.inflow_repo.ler_inflow_acumulado()
        inflow = pd.concat ([inflow_novo,inflow_acumulado],ignore_index=True)
        inflow['numero_residente'] = inflow['numero_residente'].astype(str).pipe(pd.to_numeric, errors="coerce").astype("Int64")
        self.inflow_repo.salvar_inflow_acumulado(inflow)
            
        logger.info(f"✅ Inflow atualizado: {len(inflow_acumulado)} → {len(inflow)} registos")
        return True

    def calcular_distribuicao(self, df_validado):      #prepara os valores a considerar (mensalidade, PIM ou ambos)
        if df_validado.empty:
            return pd.DataFrame()
        df_validado["Num_num"] = pd.to_numeric(df_validado["numero_residente"], errors='coerce')   #para compara com 0
        df = df_validado[df_validado["Num_num"] > 0].copy()
        df = df.drop(columns=["Num_num"])
        if df.empty:
            return pd.DataFrame()
        pim_df = self.pim_repo.ler_pim()
        df = df.merge(pim_df[["numero_residente", "saldo"]],on="numero_residente",how="left",)
        df["saldo"] = df["saldo"].fillna(0.0)
        df["valor_PIM"] = 0.0
        df["valor_mensalidade"] = 0.0
        mask_pim = df["tipo"] == "PIM"
        mask_mens = df["tipo"] == "mensalidade"
        mask_combo = df["tipo"] == "mensalidade + PIM"
        df.loc[mask_pim, "valor_PIM"] = df["valor"]
        df.loc[mask_mens, "valor_mensalidade"] = df["valor"]
        df.loc[mask_combo, "valor_PIM"] = (df.loc[mask_combo][["valor", "saldo"]].min(axis=1))
        df.loc[mask_combo, "valor_mensalidade"] = (df.loc[mask_combo, "valor"]- df.loc[mask_combo, "valor_PIM"])
        return df
        
    def aplicar_efeitos_financeiros(self, df_calculado):
        """
        Aplica consequências financeiras dos movimentos já validados.
        NÃO envia emails.
        NÃO preenche data_envio_recibo.
        """
        # atualizar PIM
        df_pim = df_calculado[df_calculado["tipo"] == "PIM"].copy()
        pim_df, recibos_pendentes = self._atualizar_pim(df_pim)
        self.pim_repo.salvar_pim(pim_df)
        self.pim_repo.guardar_recibos_pendentes(recibos_pendentes)
        return {
        "pim_atualizado": len(df_pim),
        "recibos": len(recibos_pendentes)
    }

    def _atualizar_pim(self, df):
        """
        atualiza o ficheiro PIM com os novos movimentos classificados.
        Guarda recibos_pendentes para envio aos residentes.
        """        
        pim_df = self.pim_repo.ler_pim()                               # Ler PIM
        df_mov = df[['numero_residente','data','valor']].rename(columns={'valor':'recebido'}).copy()     
        df_mov = (df_mov.groupby('numero_residente', as_index=False).agg(data=('data', 'max'),recebido=('recebido', 'sum')))
        pim_df['numero_residente'] = pim_df['numero_residente'].astype(str).str.strip().pipe(pd.to_numeric, errors="coerce").astype("Int64")
        df_mov['numero_residente'] = df_mov['numero_residente'].astype(str).str.strip().pipe(pd.to_numeric, errors="coerce").astype("Int64")
        # Usar map() para as atualizações
        mascara = pim_df['numero_residente'].isin(df_mov['numero_residente'])
        # Mapeamentos
        mapa_data = df_mov.set_index('numero_residente')['data']
        mapa_recebido = df_mov.set_index('numero_residente')['recebido']
        pim_df.loc[mascara, 'data'] = pim_df.loc[mascara, 'numero_residente'].map(mapa_data)
        pim_df.loc[mascara, 'recebido'] += pim_df.loc[mascara, 'numero_residente'].map(mapa_recebido)
        saldo = (pim_df.loc[mascara, "total"] - pim_df.loc[mascara, "recebido"]).round(2)
        pim_df.loc[mascara, "saldo"] = saldo.where(saldo.abs() >= 0.01, 0)    
        recibos_pendentes = pim_df.loc[mascara]
        breakpoint()
        recibos_pendentes = recibos_pendentes[["numero_residente","nome","anterior","recebido","saldo","data","data_envio_recibo"]]
        pim_df['numero_residente'] = pim_df['numero_residente'].astype("Int64")
        return pim_df,recibos_pendentes

    def _enviar_recibos(self, df_recibos=None):
        pim_df = self.pim_repo.ler_pim()        
        builder =self.template_builder
        df_recibos = self.pim_repo.ler_recibos_pendentes()
        residentes_list= self.residentes_repo.get_all()
        residentes_df =pd.DataFrame(residentes_list)
        df_recibos["numero_residente"] = df_recibos["numero_residente"].astype(str)
        residentes_df["numero_residente"] = residentes_df["numero_residente"].astype(str)
        df = df_recibos.merge(residentes_df[["numero_residente", "genero", "relacao", "petit_nom", "responsavel", "email"]],
            on="numero_residente",how="left")
        df_envio = (df.loc[df["data_envio_recibo"].isna() & df["email"].notna()]
            .assign(genero=lambda x: x["genero"].fillna(""),petit_nom=lambda x: x["petit_nom"].fillna("")))
        if df_envio.empty:     return df
        mensagens = []
        for row in df_envio.itertuples():
            if row.saldo != 0:
                bloco_saldo = f"A conta de medicação fica com um saldo de {row.saldo:.2f} €."
            else:
                bloco_saldo = ""
            subject, html = builder.build(
                "recibo_PIM.docx",
                {
                    "nome": row.nome,
                    "data": row.data,
                    "recebido": f"{row.recebido:.2f}",
                    "saldo": f"{row.saldo:.2f}",
                    "bloco_saldo": bloco_saldo
                }
            )
            mensagens.append(
                EmailMessage(
                    to=[row._asdict()["email"]],
                    subject=subject,
                    html_body=html,
                )
            )
        sender = EmailSender(
            self.emailer,
            modo_teste=self.modo_teste,)
        sender.send_batch(
            mensagens=mensagens,
            log_dir = self.cfg.email_logs,
            on_progress=None,
        )
        timestamp = datetime.now().strftime("%Y-%m-%d")

        df.loc[df_envio.index, "data_envio_recibo"] = timestamp
        ids_enviados = df_envio["numero_residente"].astype(str)
        pim_df["numero_residente"] = pim_df["numero_residente"].astype(str)
        mask = pim_df["numero_residente"].isin(ids_enviados)
        pim_df.loc[mask, "data_envio_recibo"] = timestamp
        self.pim_repo.salvar_pim(pim_df)
        self.pim_repo.guardar_recibos_pendentes(df_recibos)
        return len(mensagens)
            
    def produzir_dd(self):
        residentes = self.residentes_repo.get_all()
        df_res = pd.DataFrame(residentes)
        df_cc = self.conta_corrente_repo.get_all()
        #df_cc = pd.DataFrame(cc)
        df_cc = df_cc[df_cc["excepcao"].isin(["DD","SemPIM"])].copy()
        breakpoint()
        df_cc=df_cc[["numero_residente","excepcao","nome","pim","atual"]]
        df_cc["pim"] = df_cc["pim"].fillna(0.0)
        df_cc["excepcao"] = df_cc["excepcao"].str.strip().str.lower()
        df_cc["valor_final"] = np.where(
            df_cc["excepcao"] == "sempim",
            df_cc["atual"],
            df_cc["atual"]+df_cc["pim"].round(2)
        )
        df = df_cc.merge(
            df_res[["numero_residente","iban","data_iban"]],
            on="numero_residente")
        
        df["RCUR"] = "RCUR"
        df["nome"]=df["nome"].astype(str).apply(simplificar_nome).apply(normalizar_nome)
        df["espaco"] = ""
        df = df[[
            "iban",
            "espaco",
            "valor_final",
            "RCUR",
            "numero_residente",
            "data_iban",
            "nome"
        ]]
        # formatar para texto com vírgula decimal
        df["valor_final"] = df["valor_final"].map(lambda x: f"{x:.2f}".replace(".", ","))
        df["data_iban"] = (pd.to_datetime(df["data_iban"], errors="coerce").dt.strftime("%d-%m-%Y"))
        path = self.paths["debitodireto_file"]     
        df.to_csv(
            path,
            sep="\t",
            index=False,
            header=False
        )
        return path

    def processar_dd(self, atualizar_pim=True, enviar_emails=True):
        inflow, data = self.inflow_repo.ler_comprovativodd()
        inflow["estado"] = (inflow["estado"].astype(str).str.strip().str.strip("'")) #remove espaços e aspas simples
        inflow = inflow[inflow["estado"]=="0000"] 
        inflow["numero_residente"] = (inflow["numero_residente"].astype(str).str.strip().str.strip("'"))       
        inflow["numero_residente"] = inflow["numero_residente"].astype(str).str.strip()
        inflow["numero_residente"] = inflow["numero_residente"].apply(
                                    lambda x: x[:-1] if isinstance(x, str) and len(x) == 4 else x)
        if inflow.empty:
            return 0
        cc = pd.DataFrame(self.conta_corrente_repo.get_all())
        df = inflow.merge(cc,on="numero_residente")
        df["valor"] = (df["valor"] - df["mensalidade"]).round(2)
        df = df[df["valor"]>0]
        df["data"]=data
        if atualizar_pim:
            self._atualizar_pim(df)
        if enviar_emails:
            self._enviar_recibos(df)
        return len(df)

    def existe_comprovativodd(self):
        return self.paths["comprovativodd_file"].exists()

    def carregar_extrato_diario(self):
        return {
            "extrato": self.inflow_repo.ler_extrato_diario(),
            "inflow": self.inflow_repo.ler_inflow_acumulado(),
        }

    def get_residentes_lookup(self) -> dict[int, str]:

            lookups = self.residentes_repo.get_residentes_lookups()

            return lookups.get("numero_nome", {})