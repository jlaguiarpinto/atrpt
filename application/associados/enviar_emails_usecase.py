# application/associados/enviar_emails_usecase.py
"""
Caso de uso para envio de emails para associados
Com fluxo: Preparar → Analisar → Enviar
"""
import logging
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass
from tkinter import messagebox
import logging

from application.email.email_template_builder import EmailTemplateBuilder
from application.email.email_message import EmailMessage
from application.email.email_sender import EmailSender
from infrastructure.persistence.associados_repository import AssociadosRepo
from infrastructure.persistence.envio_repository import EnvioRepository
from domain.shared.strings import simplificar_nome



@dataclass
class AnalisePreparacao:
    """Resultado da análise da preparação"""
    total_mensagens: int
    emails_validos: int
    emails_invalidos: int
    campos_encontrados: List[str]
    campos_faltantes: List[str]
    placeholders_template: List[str]
    placeholders_nao_encontrados: List[str]
    preview_mensagens: pd.DataFrame
    estatisticas: Dict[str, Any]
    recomendacoes: List[str]


class EnviarEmailsAssociadosUseCase:
    """Caso de uso para envio de emails para associados com fluxo em 3 fases"""
    
    def __init__(self, 
                 repo_associados: AssociadosRepo, 
                 email_sender: EmailSender,
                 envio_repository: Optional[EnvioRepository] = None
                 ):
        """
        Inicializa o caso de uso
        
        Args:
            repo_associados: Repositório de associados (com método ler_associados)
            emailer: Serviço de envio de emails (Emailer)
            email_sender: Serviço de envio com batch (EmailSender) - opcional
            envio_repository: Repositório para guardar informações de envio
        """
        self.repo_associados = repo_associados
        self.email_sender = email_sender
        self.envio_repository = envio_repository
        self.logger = logging.getLogger(__name__)
        
        # Armazenar estado entre fases
        self._mensagens_preparadas = None
        self._assunto_log = None
        self._subject_template = None
        self.ficheiro_envio = None

    def preparar(self, template_path: str, anexos=None) -> dict:

        df = self.repo_associados.ler_associados()

        if df.empty:
            return {"status": "erro", "mensagem": "Sem dados"}

        # validação
        df = df[df["email"].notna()]
        df = df[df["email"].str.contains("@")]

        # transformação
        if "nome" in df.columns:
            df["nome"] = df["nome"].apply(simplificar_nome)
        else:
            df["nome"] = ""
        if "sexo" in df.columns:
            df["sexo"] = df.get("sexo", "").map({"M": "o", "F": "a"}).fillna("")
        else:
            df["sexo"] = ""

        # render
        builder = EmailTemplateBuilder(template_dir=Path(template_path).parent)
        template_name = Path(template_path).name

        def build_row(row):
            subject, html = builder.build(template_name, row.to_dict())
            return subject, html

        res = df.apply(build_row, axis=1)
        df["subject"] = [r[0] for r in res]
        df["html_body"] = [r[1] for r in res]

        df["attachments"] = ";".join(anexos) if anexos else ""

        print(df[["email", "subject", "html_body"]].head())
        print(template_name)
        ficheiro = self.envio_repository.guardar(df, template_name)

        return {
            "ficheiro_envio": str(ficheiro),
            "total": len(df)
        }

    def analisar(self, ficheiro_envio: str, preview_n=5):

        df = pd.read_excel(ficheiro_envio)

        total = len(df)
        validos = df["email"].notna().sum()

        preview = df.head(preview_n)

        return {
            "total": total,
            "validos": validos,
            "invalidos": total - validos,
            "preview": preview
        }

    def enviar(self, ficheiro_envio: str, on_progress=None):

        df = pd.read_excel(ficheiro_envio)

        df = df[df["dataenvio"].isna()]

        mensagens = []

        for _, row in df.iterrows():

            msg = EmailMessage(
                to=[row["email"]],
                subject=row["subject"],
                html_body=row["html_body"],
                attachments=self._parse_attachments(row.get("attachments"))
            )

            mensagens.append(msg)

        resultado = self.email_sender.send_batch(
            mensagens=mensagens,
            df=df,
            ficheiro_envio=Path(ficheiro_envio),
            on_progress=on_progress
        )

        return {
            "status": "ok",
            "enviados": resultado["stats"]["ok"],
            "erros": resultado["stats"]["erro"]
        }

    def preparar_filtros(df, filtros=None):

        if filtros:
            if "idade_min" in filtros:
                df = df[df["idade"] >= filtros["idade_min"]]

            if "saldo_min" in filtros:
                df = df[df["saldo"] >= filtros["saldo_min"]]

    def _parse_attachments(self, value):
        if pd.isna(value) or not value:
            return []
        return [Path(v) for v in str(value).split(";") if v.strip()]
   
    def construir_df_envio(self) -> pd.DataFrame:
        """
        Constrói o dataFrame com os dados dos associados.
        Usa o método ler_associados() do repositório.
        """
        try:

            df = self.repo_associados.ler_associados()
            
            self.logger.info(f"Dados carregados: {len(df)} associados ativos com email")
                      
            # Garantir que tem as colunas necessárias
            if 'email' not in df.columns:
                raise ValueError("Coluna 'email' não encontrada após carregamento")
            
            # Adicionar coluna saldo se existir o ficheiro de saldos
            if hasattr(self.repo_associados, 'ler_saldos'):
                try:
                    df_saldos = self.repo_associados.ler_saldos()
                    self.logger.info.info(f"saldos carregados: {len(df_saldos)} registos")
                    # Fazer merge com saldos (assumindo que há uma coluna de ID comum)
                    if 'id' in df.columns and 'id' in df_saldos.columns:
                        df = df.merge(df_saldos[['id', 'saldo']], on='id', how='left')
                        self.logger.info.info("saldos integrados com sucesso")
                except Exception as e:
                    self.logger.info.warning(f"Não foi possível carregar saldos: {e}")
            
            return df
            
        except Exception as e:
            self.logger.info.error(f"Erro ao carregar dados do repositório: {e}")
            self.logger.info.exception("Detalhes do erro:")
            raise
        return df
          
    def _carregar_dados(self):                          #leitura do ficheiro base

        df = self.repo_associados.ler_associados()
        if df is None or df.empty:
            raise ValueError("Sem dados de associados")
        self.logger.info.info(f"Dados carregados: {len(df)} registos")
        return df

    def _validar_email(self, df):                       #validação básica dos dados (email)        
        if "email" not in df.columns:
            raise ValueError("Coluna 'email' não encontrada")
        df = df[df["email"].notna()]
        df = df[df["email"].astype(str).str.contains("@")]
        self.logger.info.info(f"Emails válidos: {len(df)}")
        return df

    def _tratar_campos(self, df):                       #tratar campos opcionais (sexo, nome)  

        if "sexo" in df.columns:
            df["sexo"] = df["sexo"].map({"M": "o", "F": "a"}).fillna("")
        else:
            df["sexo"] = ""

        if "nome" in df.columns:
            df["nome"] = df["nome"].apply(simplificar_nome)
        else:
            df["nome"] = ""

        return df

    def _carregar_template(self, template_path):        #carregar template e extrair subject, body e placeholders

        subject, body, placeholders = self._subject_template(template_path)
        self.logger.info.info(f"Placeholders encontrados: {placeholders}")
        return subject, body, placeholders

    def _renderizar(self, df, builder, template_name):

        total = len(df)
        self.logger.info.info(f"🔄 Renderizando {total} mensagens...")

        def build_row(row):
            data = row.to_dict()
            subject, html = builder.build(template_name, data)
            return subject, html

        results = df.apply(build_row, axis=1)

        df["subject"] = [r[0] for r in results]
        df["html_body"] = [r[1] for r in results]

        return df
    
         
    def enviar_emails(self,
                    df_envio: pd.DataFrame,
                    ficheiro_envio: str,
                    anexo_paths: Optional[list] = None,
                    on_progress: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Envia emails a partir de um DataFrame já filtrado
        """
        
        self.logger.info("=" * 60)
        self.logger.info("ENVIO DE EMAILS")
        self.logger.info("=" * 60)
        
        if on_progress:
            on_progress("📧 Iniciando envio...")
        
        if df_envio.empty:
            return {"status": "erro", "mensagem": "Nenhum email para enviar"}
        
        ficheiro_path = Path(ficheiro_envio)
        
        # Validar colunas
        if 'email' not in df_envio.columns:
            return {"status": "erro", "mensagem": "Coluna 'email' não encontrada"}
        
        if 'html_body' not in df_envio.columns:
            return {"status": "erro", "mensagem": "Coluna 'html_body' não encontrada"}
        
        if 'subject' not in df_envio.columns:
            df_envio['subject'] = ""
        
        # Construir mensagens

                
        if on_progress:
            on_progress(f"📧 Preparando {len(df_envio)} mensagens...")
        
        from application.email.email_message import EmailMessage
        
        mensagens_para_envio = []
        indices_validos = []
        
        for idx, row in df_envio.iterrows():
            email = row["email"]
            if pd.isna(email) or not str(email).strip():
                continue
            
            msg = EmailMessage(
                to=[str(email)],
                subject=str(row["subject"]) if not pd.isna(row["subject"]) else "",
                html_body=str(row["html_body"]) if not pd.isna(row["html_body"]) else "",
                attachments=parse_attachments(row["attachments"]),
                inline_images={},
                bcc=[]
            )
            mensagens_para_envio.append(msg)
            indices_validos.append(idx)
        
        df_final = df_envio.loc[indices_validos].copy()
        
        if on_progress:
            on_progress(f"✅ {len(mensagens_para_envio)} mensagens válidas")
        
        if len(mensagens_para_envio) == 0:
            return {"status": "erro", "mensagem": "Nenhuma mensagem válida"}
        
        # Enviar
        from application.email.email_sender import EmailSender
        
        email_sender = EmailSender(
            emailer=self.emailer,
            modo_teste=getattr(self.emailer, "modo_teste", False),
            email_teste=getattr(self.emailer, "email_teste", None),
        )
        
        assunto_log = f"envio_{datetime.now().strftime('%Y%m%d_%H%M')}"
        log_dir = Path("logs") / "associados" / assunto_log
        log_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            if on_progress:
                on_progress("🚀 Enviando emails...")
            
            def batch_progress(msg):
                self.logger.info(msg)
                if on_progress:
                    on_progress(msg)
            
            resultado = email_sender.send_batch(
                mensagens=mensagens_para_envio,
                df=df_final,
                ficheiro_envio=ficheiro_path,
                tamanho_lote=25,
                pausa_entre_lotes=(60, 120),
                delay_envio=(3, 6),
                on_progress=batch_progress,
            )
            
            relatorio_path = ficheiro_path.parent / f"relatorio_{assunto_log}.xlsx"
            df_final.to_excel(relatorio_path, index=False)
            
            if on_progress:
                on_progress("\n" + "="*50)
                on_progress("✅ ENVIO CONCLUÍDO")
                on_progress(f"Total: {resultado['total']}")
                on_progress(f"OK: {resultado['stats']['ok']}")
                on_progress(f"ERROS: {resultado['stats']['erro']}")
                on_progress("="*50)
            
            return {
                "status": "concluido",
                "total": resultado["total"],
                "enviados": resultado["stats"]["ok"],
                "erros": resultado["stats"]["erro"],
                "relatorio": str(relatorio_path),
                "log_dir": str(log_dir),
            }
            
        except Exception as e:
            self.logger.exception("Erro no envio")
            if on_progress:
                on_progress(f"❌ Erro: {str(e)}")
            
            return {
                "status": "erro",
                "mensagem": str(e)
            }

    def _finalizar_envio(self, resultado):
        """Callback chamado pelo controller quando o envio termina"""
        self.enviando = False
        self.progress.pack_forget()
        
        if resultado is None:
            self.logger.info("❌ Erro: Resultado None")
            messagebox.showerror("Erro", "Erro no envio: resultado vazio")
            return
        
        if resultado.get("status") == "concluido":
            self.logger.info(f"\n✅ ENVIO CONCLUÍDO")
            self.logger.info(f"   Enviados: {resultado.get('enviados', 0)}")
            self.logger.info(f"   Erros: {resultado.get('erros', 0)}")
            
            # Atualizar informações do ficheiro
            try:
                df = pd.read_excel(self.ficheiro_envio)
                if 'data_envio' in df.columns:
                    pendentes = df[df['data_envio'].isna() | (df['data_envio'] == '')].shape[0]
                    self.logger.info(f"📊 Restam pendentes: {pendentes}")
            except:
                pass
            
            messagebox.showinfo(
                "Envio Concluído",
                f"Envio finalizado!\n\n"
                f"Enviados: {resultado.get('enviados', 0)}\n"
                f"Erros: {resultado.get('erros', 0)}"
            )
        else:
            erro_msg = resultado.get('mensagem', 'Erro desconhecido')
            self.logger.info(f"❌ Erro: {erro_msg}")
            messagebox.showerror("Erro", f"Erro no envio:\n{erro_msg}")

    def _erro_envio(self, erro):
        """Trata erro no envio"""
        self.enviando = False
        self.progress.pack_forget()
        self.logger.info(f"❌ Erro: {erro}")
        messagebox.showerror("Erro", f"Erro no envio:\n{erro}")


"""

    def preparar(
        self,
        template_path: str,
        anexos: Optional[List[str]] = None,
        on_progress: Optional[Callable] = None
    ) -> Dict[str, Any]:

        try:
            self.logger.info.info("FASE 1: PREPARAÇÃO DAS MENSAGENS")
            if on_progress:
                on_progress("📝 Preparando mensagens...")

            df = self._carregar_dados()
            df = self._validar_email(df)
            df = self._tratar_campos(df)

            builder = EmailTemplateBuilder(template_dir=Path(template_path).parent)

            template_name = Path(template_path).name

            if on_progress:
                on_progress(f"🔄 Renderizando {len(df)} mensagens...")

            df = self._renderizar(df, builder, template_name)

            anexos_str = ";".join(anexos) if anexos else ""
            df["attachments"] = anexos_str

            assunto_log = Path(template_name).stem

            self.logger.info.info(f"✅ Preparação concluída. total de mensagens: {len(df)}")

            base_nome = Path(template_name).stem
            base_nome = re.sub(r"[^\w\-_.]", "_", base_nome)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            nome_ficheiro = f"{base_nome}_{timestamp}.xlsx"
            subdir = Path("associados/envio_emails")
            path = subdir / nome_ficheiro
            ficheiro = self.envio_repository.guardar(
                df=df,
                path=path,
            )

            self.logger.info(f"📁 Ficheiro de envio criado: {ficheiro}")

            return {
                "status": "ok",
                "df": df,
                "total": len(df),
                "ficheiro_envio": str(ficheiro)
}

        except Exception as e:
            self.logger.exception("Erro na preparação")

            if on_progress:
                on_progress(f"❌ Erro: {str(e)}")

            return {
                "status": "erro",
                "mensagem": str(e)
            }

       def analisar(self, 
                 preview_n: int = 5,
                 on_progress: Optional[Callable] = None) -> AnalisePreparacao:
       
        Fase 2: Analisa as mensagens preparadas
        
        Args:
            preview_n: Número de mensagens para preview
            on_progress: Callback para atualizar progresso na UI
            
        Returns:
            AnalisePreparacao com todos os dados da análise
        
        
        self.logger.info.info("=" * 60)
        self.logger.info.info("FASE 2: ANÁLISE DAS MENSAGENS")
        self.logger.info.info("=" * 60)
        
        if self._mensagens_preparadas is None:
            raise ValueError("Nenhuma mensagem preparada. Execute preparar() primeiro.")
        
        df = self._mensagens_preparadas
        
        total = len(df)
        emails_validos = df['email'].notna().sum()
        emails_invalidos = total - emails_validos
        
        campos_encontrados = list(df.columns)
        
        # Estatísticas
        estatisticas = {
            "total_mensagens": total,
            "total_unicos": df['email'].nunique(),
            "tamanho_medio_html": df['html_body'].str.len().mean() if len(df) > 0 else 0,
            "dominios_email": df['email'].str.split('@').str[1].value_counts().head(5).to_dict() if len(df) > 0 else {}
        }
        
        # Preview
        preview = df.head(preview_n).copy()
        
        # Recomendações
        recomendacoes = []
        if emails_invalidos > 0:
            recomendacoes.append(f"⚠️ {emails_invalidos} emails inválidos serão ignorados")
        
        if estatisticas["tamanho_medio_html"] > 50000:
            recomendacoes.append("⚠️ HTML muito grande (>50KB) - pode afetar entrega")
        
        # Mostrar preview no log
        self.logger.info.info("\n📧 PREVIEW DAS PRIMEIRAS MENSAGENS:")
        for i, row in preview.iterrows():
            self.logger.info.info(f"\n[{i+1}] Para: {row['email']}")
            self.logger.info.info(f"    Nome: {row.get('nome', 'N/A')}")
            self.logger.info.info(f"    Assunto: {row['subject'][:60]}...")
        
        if on_progress:
            on_progress(f"\n📊 Análise: {total} mensagens, {estatisticas['total_unicos']} emails únicos")
            for rec in recomendacoes:
                on_progress(rec)
        
        return AnalisePreparacao(
            total_mensagens=total,
            emails_validos=emails_validos,
            emails_invalidos=emails_invalidos,
            campos_encontrados=campos_encontrados,
            campos_faltantes=[],
            placeholders_template=[],
            placeholders_nao_encontrados=[],
            preview_mensagens=preview,
            estatisticas=estatisticas,
            recomendacoes=recomendacoes
        )
         




"""