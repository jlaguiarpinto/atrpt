#atrpt/infrastructure/logging_associados.py
import logging
import csv
from datetime import datetime
from pathlib import Path
from typing import Optional

class AssociadosLogger:
    """Sistema de logging específico para envios de associados"""
    
    def __init__(self, assunto: str, pasta_logs: str = "logs/associados"):
        """
        Inicializa o logger com o assunto do template
        
        Args:
            assunto: Subject do template (já normalizado)
            pasta_logs: Diretório base para os logs
        """
        self.assunto = assunto
        self.pasta_logs = Path(pasta_logs)
        self.pasta_logs.mkdir(parents=True, exist_ok=True)
        
        # Criar nome do ficheiro de log baseado no assunto e timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_base = f"{assunto}_{timestamp}"
        self.log_file = self.pasta_logs / f"{nome_base}.log"
        self.detalhes_file = self.pasta_logs / f"{nome_base}_detalhes.csv"
        
        # Configurar logger específico
        self.logger = logging.getLogger(f"envio_associados.{assunto}")
        self.logger.setLevel(logging.INFO)
        
        # Remover handlers existentes para evitar duplicação
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        # Handler para ficheiro
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # Formato detalhado
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        # Adicionar handler
        self.logger.addHandler(file_handler)
        
        # Opcional: adicionar também handler para console se quiser
        # console_handler = logging.StreamHandler()
        # console_handler.setFormatter(formatter)
        # self.logger.addHandler(console_handler)
    
    def iniciar_envio(self, total_emails: int, modo_teste: bool = False):
        """Regista o início do envio"""
        self.logger.info("=" * 80)
        self.logger.info(f"INÍCIO DO ENVIO - Assunto: {self.assunto}")
        self.logger.info(f"total de emails: {total_emails}")
        self.logger.info(f"Modo teste: {'ATIVADO' if modo_teste else 'DESATIVADO'}")
        self.logger.info("=" * 80)
        
        # Inicializar ficheiro CSV de detalhes
        with open(self.detalhes_file, 'w', encoding='utf-8-sig') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(["data/Hora", "Índice", "nome, "Email", "Status", "Mensagem", "Tempo(s)"])
    
    def registar_envio(self, index: int, nome: str, email: str, status: str, 
                      mensagem: str, tempo: float = None):
        """Regista o envio individual no log e no CSV"""
        # Log no ficheiro principal
        status_emoji = "✅" if status == "OK" else "❌"
        tempo_str = f" - {tempo:.2f}s" if tempo else ""
        self.logger.info(f"[{index}] {status_emoji} {nome} <{email}> - {mensagem}{tempo_str}")
        
        # Registar no CSV
        try:
            with open(self.detalhes_file, 'a', encoding='utf-8-sig') as f:
                writer = csv.writer(f, delimiter=';')
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                tempo_str_csv = f"{tempo:.2f}" if tempo else ""
                writer.writerow([timestamp, index, nome, email, status, mensagem, tempo_str_csv])
        except Exception as e:
            self.logger.error(f"Erro ao escrever no CSV: {e}")
    
    def registar_pausa(self, duracao: int, batch_atual: int):
        """Regista uma pausa no envio"""
        self.logger.info(f"⏸️ PAUSA ESTRATÉGICA - Batch {batch_atual} - Duração: {duracao}s")
    
    def registar_checkpoint(self, index: int, total: int):
        """Regista um checkpoint (salvamento do Excel)"""
        self.logger.info(f"📌 CHECKPOINT - {index}/{total} emails processados")
    
    def registar_erro(self, erro: str, detalhes: str = None):
        """Regista um erro geral"""
        self.logger.error(f"ERRO: {erro}")
        if detalhes:
            self.logger.debug(detalhes)
    
    def finalizar_envio(self, total: int, enviados: int, erros: int, 
                        tempo_total: float, ficheiro_excel: str = None):
        """Regista o fim do envio com estatísticas"""
        taxa_sucesso = (enviados / total * 100) if total > 0 else 0
        taxa_erro = (erros / total * 100) if total > 0 else 0
        
        self.logger.info("=" * 80)
        self.logger.info("FIM DO ENVIO - RESUMO FINAL")
        self.logger.info(f"total processado: {total}")
        self.logger.info(f"Enviados com sucesso: {enviados} ({taxa_sucesso:.1f}%)")
        self.logger.info(f"Erros: {erros} ({taxa_erro:.1f}%)")
        self.logger.info(f"Tempo total: {tempo_total:.2f}s ({tempo_total/60:.1f} minutos)")
        if ficheiro_excel:
            self.logger.info(f"Ficheiro Excel: {ficheiro_excel}")
        self.logger.info(f"Log detalhado: {self.detalhes_file}")
        self.logger.info("=" * 80)
        
        return {
            "log_file": str(self.log_file),
            "detalhes_file": str(self.detalhes_file)
        }