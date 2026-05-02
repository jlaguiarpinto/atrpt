# application/secretaria/processar_ponto_usecase.py
import logging
import pandas as pd
from domain.secretaria.ponto_processor import PontoProcessor

logger = logging.getLogger(__name__)


class ProcessarPontoUseCase:

    def __init__(self):
        self.processor = PontoProcessor()

    def executar(self, repo, ctx, on_progress=None):

        def log(msg):
            logger.info(msg)
            if on_progress:
                on_progress(msg)

        ficheiros = repo.listar_ficheiros_diarios()
        if not ficheiros:
            log("Sem ficheiros diarios.")
            return 0, None
        log(f"📂 {len(ficheiros)} ficheiros encontrados")

        mensal = repo.ler_mensal()
        total  = 0
        erros_total = []

        df_dia_anterior = None
        try:
            df_raw_ant = repo.ler_ultimo_dia_mes_anterior()
            if df_raw_ant is not None:
                df_dia_anterior = self.processor.limpar_registos(df_raw_ant)
                log("📅 Ultimo dia do mes anterior carregado")
        except Exception as e:
            logger.warning(f"Nao foi possivel ler mes anterior: {e}")

        for f in ficheiros:
            log(f"📄 {f.name}")
            try:
                df_raw   = repo.ler_excel(f)
                df_limpo = self.processor.limpar_registos(df_raw)
                df_erros = self._validar_es_trocados(df_limpo)
                log(f"   - {len(df_limpo)} registos validos, {len(df_erros)} com erros")
                if not df_erros.empty:
                    erros_total.append(df_erros)
                mensal = self.processor.merge_sem_duplicados(mensal, df_limpo)
                total += 1
            except Exception as e:
                logger.error(f"Erro em {f.name}: {e}", exc_info=True)
                log(f"Erro em {f.name}: {e}")

        if mensal is None or mensal.empty:
            log("Sem dados validos.")
            return total, None

        # observações — string vazia (nunca NaN)
        for col in ["observacoes_dl", "observacoes_cs"]:
            if col not in mensal.columns:
                mensal[col] = ""
            else:
                mensal[col] = mensal[col].fillna("")

        # numéricos — inicializar a 0 / 0.0 conforme tipo
        for col in ["falta", "feriado", "ferias", "baixa", "subsidio_refeicao"]:
            if col not in mensal.columns:
                mensal[col] = 0
        for col in ["presenca", "noturno"]:
            if col not in mensal.columns:
                mensal[col] = 0.0

        for col in ["e1", "s1", "e2", "s2", "data", "nome"]:
            if col not in mensal.columns:
                mensal[col] = None

        mensal = self._calcular_presenca(mensal)
        mensal = self._aplicar_regras_negocio(mensal, df_dia_anterior)
        mensal = self._split_numero_nome(mensal)
        mensal = mensal.sort_values(["numero", "nome", "data"])
        mensal = self._adicionar_dia_semana_feriado(mensal)
        mensal = self._juntar_erros(mensal, erros_total)
        mensal = self._split_numero_nome(mensal)           # número disponível antes de classificar
        mensal = self._classificar_grupo(mensal)           # AAD / Enfermeiro por numero >= 500
        # calcular feriados do mês para os enfermeiros
        _anos_enf = pd.to_datetime(mensal["data"], errors="coerce").dt.year.dropna().unique()
        _feriados_enf = {}
        for _ano in _anos_enf:
            _feriados_enf.update(self._feriados_ano(int(_ano)))
        mensal = self._calcular_horas_enfermeiro(mensal, _feriados_enf)
        mensal = self._transformar_colunas(mensal)

        colunas_finais = [
            "data", "dia_semana", "feriado_desc",
            "numero", "nome", "grupo", "e1", "s1", "e2", "s2",
            "presenca", "falta", "feriado", "ferias",
            "noturno", "baixa", "subsidio_refeicao",
            "diurno_h", "noturno_h", "domingo_h",
            "erros_picagem",
            "observacoes_dl", "observacoes_cs",
        ]
        mensal = mensal[[c for c in colunas_finais if c in mensal.columns]]
        mensal = self._adicionar_totais(mensal)

        try:
            repo.guardar_mensal(mensal)
            output = repo.ficheiro_resumo
            log(f"Resumo gravado em: {output}")
        except Exception as e:
            logger.error(f"Erro ao gravar resumo: {e}", exc_info=True)
            log(f"Erro ao gravar resumo: {e}")
            return total, None

        try:
            resumo = self._gerar_resumo(mensal)
            repo.guardar_resumo_empregado(resumo)
            log("Resumo por empregado gravado")
        except Exception as e:
            logger.error(f"Erro ao gravar resumo por empregado: {e}", exc_info=True)

        n_erros = mensal["erros_picagem"].astype(bool).sum() if "erros_picagem" in mensal.columns else 0
        if n_erros:
            log(f"⚠️ {n_erros} linhas com erros de picagem (ver coluna erros_picagem)")
        else:
            log("Sem erros de picagem")

        log(f"\n✔ {total} ficheiros processados")
        return total, output

    # ──────────────────────────────────────────────────────────────────────────

    def _calcular_presenca(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        p = self._parse_hora

        def _horas(row):
            total = 0.0
            for ce, cs in [("e1","s1"), ("e2","s2")]:
                ev = str(row.get(ce, "")).strip().upper()
                sv = str(row.get(cs, "")).strip().upper()
                if ev.startswith("S") or sv.startswith("E"):
                    continue
                e_h = p(row.get(ce))
                s_h = p(row.get(cs))
                if e_h is None or s_h is None:
                    continue
                if s_h <= e_h:
                    continue
                dur = (s_h.hour*60 + s_h.minute - e_h.hour*60 - e_h.minute) / 60
                if 0 < dur < 24:
                    total += dur
            return round(total, 2)

        df["presenca"] = df.apply(_horas, axis=1)
        return df

    def _aplicar_regras_negocio(self, df, df_dia_anterior=None):
        df = df.copy()
        df["subsidio_refeicao"] = (pd.to_numeric(df["presenca"], errors="coerce") > 0).astype(int)
        df["noturno"] = 0.0

        for col in ["presenca", "falta", "feriado", "ferias", "baixa"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").round(2)

        try:
            data_min = pd.to_datetime(df["data"], errors="coerce").min()
        except Exception:
            data_min = None

        mapa_anterior = {}
        if df_dia_anterior is not None:
            for _, row_ant in df_dia_anterior.iterrows():
                nome_ant = str(row_ant.get("nome", "")).strip().upper()
                e1_ant   = str(row_ant.get("e1",   "")).strip()
                try:
                    h = self._parse_hora(e1_ant)
                    if h is not None and h.hour >= 18:
                        mapa_anterior[nome_ant] = h
                except Exception:
                    pass

        df["noturno"] = self._calcular_noturno(df, data_min, mapa_anterior)
        df["subsidio_refeicao"] = (
            (pd.to_numeric(df["presenca"], errors="coerce") > 0) |
            (pd.to_numeric(df["noturno"],  errors="coerce") > 0)
        ).astype(int)
        return df

    @staticmethod
    def _parse_hora(val):
        if val is None:
            return None
        s = str(val).strip()
        if s.upper().startswith(("E", "S")):
            s = s[1:].strip()
        try:
            h = pd.to_datetime(s, errors="coerce")
            return None if pd.isna(h) else h
        except Exception:
            return None

    def _calcular_noturno(self, df, data_min, mapa_anterior) -> pd.Series:
        result = pd.Series(0.0, index=df.index)
        p = self._parse_hora

        for nome, grupo in df.groupby("nome", sort=False):
            grupo = grupo.sort_values("data").copy()
            datas = pd.to_datetime(grupo["data"], errors="coerce")
            idx_list = list(grupo.index)

            for pos, idx in enumerate(idx_list):
                row    = grupo.loc[idx]
                data_p = datas.loc[idx]
                e1_p   = p(row.get("e1"))
                s1_p   = p(row.get("s1"))
                e1_str = str(row.get("e1", "")).strip().upper()
                s1_str = str(row.get("s1", "")).strip().upper()

                if pd.isna(data_p):
                    continue

                e_primeiro = (data_min is not None and
                              not pd.isna(data_p) and
                              data_p.date() == data_min.date())

                if e_primeiro and s1_p is not None and (e1_p is None or e1_str.startswith("S")):
                    nome_up = str(nome).strip().upper()
                    e1_ant  = mapa_anterior.get(nome_up)
                    if e1_ant is not None:
                        dt_e = pd.Timestamp.combine(
                            data_p.date() - pd.Timedelta(days=1), e1_ant.time())
                        dt_s = pd.Timestamp.combine(data_p.date(), s1_p.time())
                        if dt_s > dt_e:
                            result[idx] = round((dt_s - dt_e).total_seconds() / 3600, 2)
                    continue

                if e1_p is None or e1_str.startswith("S"):
                    continue
                if e1_p.hour < 18:
                    continue

                dt_e = pd.Timestamp.combine(data_p.date(), e1_p.time())

                def _buscar_saida_dia_seguinte():
                    if pos + 1 >= len(idx_list):
                        return None, None
                    idx_next  = idx_list[pos + 1]
                    row_next  = grupo.loc[idx_next]
                    data_next = datas.loc[idx_next]
                    if pd.isna(data_next):
                        return None, None
                    if data_next.date() != data_p.date() + pd.Timedelta(days=1):
                        return None, None
                    s1_next = p(row_next.get("s1"))
                    e1_next = str(row_next.get("e1", "")).strip().upper()
                    if s1_next is not None and (e1_next == "" or e1_next.startswith("S")):
                        return data_next, s1_next
                    return None, None

                if s1_p is not None and not s1_str.startswith("E"):
                    dt_s = pd.Timestamp.combine(data_p.date(), s1_p.time())
                    if dt_s > dt_e:
                        result[idx] = round((dt_s - dt_e).total_seconds() / 3600, 2)
                    else:
                        data_next, s1_next = _buscar_saida_dia_seguinte()
                        if data_next is not None:
                            dt_s = pd.Timestamp.combine(data_next.date(), s1_next.time())
                            result[idx] = round((dt_s - dt_e).total_seconds() / 3600, 2)
                        else:
                            fim = pd.Timestamp.combine(
                                data_p.date(), pd.Timestamp("23:59:59").time())
                            result[idx] = round((fim - dt_e).total_seconds() / 3600, 2)
                else:
                    data_next, s1_next = _buscar_saida_dia_seguinte()
                    if data_next is not None:
                        dt_s = pd.Timestamp.combine(data_next.date(), s1_next.time())
                        result[idx] = round((dt_s - dt_e).total_seconds() / 3600, 2)
                    else:
                        fim = pd.Timestamp.combine(
                            data_p.date(), pd.Timestamp("23:59:59").time())
                        result[idx] = round((fim - dt_e).total_seconds() / 3600, 2)

        return result

    _FERIADOS_FIXOS = {
        (1,  1): "Ano Novo",
        (4, 25): "25 de Abril",
        (5,  1): "Dia do Trabalhador",
        (6, 10): "Dia de Portugal",
        (6, 24): "Sao Joao (Gaia)",
        (8, 15): "Assuncao de Maria",
        (10, 5): "Implantacao da Republica",
        (11, 1): "Todos os Santos",
        (12, 1): "Restauracao da Independencia",
        (12, 8): "Imaculada Conceicao",
        (12,25): "Natal",
    }
    _DIAS_PT = ["Segunda","Terca","Quarta","Quinta","Sexta","Sabado","Domingo"]

    @staticmethod
    def _pascoa(ano: int):
        a = ano % 19; b = ano // 100; c = ano % 100
        d = b // 4;   e = b % 4;     f = (b + 8) // 25
        g = (b - f + 1) // 3
        h = (19*a + b - d - g + 15) % 30
        i = c // 4;   k = c % 4
        l = (32 + 2*e + 2*i - h - k) % 7
        m = (a + 11*h + 22*l) // 451
        mes = (h + l - 7*m + 114) // 31
        dia = ((h + l - 7*m + 114) % 31) + 1
        import datetime
        return datetime.date(ano, mes, dia)

    def _feriados_ano(self, ano: int) -> dict:
        import datetime, datetime as dt
        feriados = {}
        for (m, d), desc in self._FERIADOS_FIXOS.items():
            try:
                feriados[datetime.date(ano, m, d)] = desc
            except ValueError:
                pass
        pascoa = self._pascoa(ano)
        feriados[pascoa - dt.timedelta(days=2)] = "Sexta-Feira Santa"
        feriados[pascoa]                         = "Pascoa"
        feriados[pascoa + dt.timedelta(days=60)] = "Corpo de Deus"
        return feriados

    def _adicionar_dia_semana_feriado(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        datas = pd.to_datetime(df["data"], errors="coerce")
        anos = datas.dt.year.dropna().unique()
        feriados = {}
        for ano in anos:
            feriados.update(self._feriados_ano(int(ano)))
        df["dia_semana"]   = datas.apply(
            lambda d: self._DIAS_PT[d.weekday()] if not pd.isna(d) else "")
        df["feriado_desc"] = datas.apply(
            lambda d: feriados.get(d.date(), "") if not pd.isna(d) else "")
        return df

    def _transformar_colunas(self, df):
        df = df.copy()

        def _f(col):
            if col not in df.columns:
                return pd.Series([0.0] * len(df), index=df.index)
            return pd.to_numeric(df[col], errors="coerce").fillna(0)

        # ── determinar fim-de-semana e feriado ────────────────────────────────
        datas = pd.to_datetime(df["data"], errors="coerce")
        eh_fds = datas.dt.weekday >= 5   # 5=Sábado, 6=Domingo

        # feriado_desc já existe se _adicionar_dia_semana_feriado foi chamado antes
        if "feriado_desc" in df.columns:
            eh_feriado = df["feriado_desc"].astype(str).str.strip() != ""
        else:
            # fallback: calcular inline
            anos = datas.dt.year.dropna().unique()
            feriados_map = {}
            for ano in anos:
                feriados_map.update(self._feriados_ano(int(ano)))
            eh_feriado = datas.apply(
                lambda d: (d.date() in feriados_map) if not pd.isna(d) else False
            )

        # ── mover horas trabalhadas em feriado de presenca → feriado ─────────
        presenca_raw = _f("presenca").apply(lambda x: round(float(x), 2))
        presenca_raw = presenca_raw.where(presenca_raw >= 0.1, 0.0)

        feriado_col = _f("feriado").apply(lambda x: round(float(x), 2))

        # quando é feriado E há horas em presença, transfere para feriado
        horas_em_feriado = presenca_raw.where(eh_feriado, 0.0)
        feriado_col = (feriado_col + horas_em_feriado).apply(lambda x: round(float(x), 2))
        presenca = presenca_raw.where(~eh_feriado, 0.0)

        df["presenca"] = presenca
        if "feriado" in df.columns:
            df["feriado"] = feriado_col

        noturno_col = pd.to_numeric(
            df.get("noturno", pd.Series([0]*len(df), index=df.index)),
            errors="coerce").fillna(0)

        # dia de saída de noturno: e1 vazio/inválido mas s1 preenchido
        # (empregado saiu de turno da noite anterior — não é falta)
        if "e1" in df.columns and "s1" in df.columns:
            e1_str = df["e1"].astype(str).str.strip().str.upper()
            s1_str = df["s1"].astype(str).str.strip()
            e1_invalido   = e1_str.isin(["", "NAN", "NONE"]) | e1_str.str.startswith("S")
            s1_valido     = ~s1_str.isin(["", "NAN", "NONE"]) & ~s1_str.str.startswith("E")
            saida_noturno = e1_invalido & s1_valido
        else:
            saida_noturno = pd.Series(False, index=df.index)

        # falta=0 ao fim-de-semana (sem picagens não é falta)
        # falta=0 em feriado (ausência em feriado não é falta)
        # falta=0 no dia de saída de turno noturno (não há presença mas não é falta)
        dia_util_sem_trabalho = (
            (presenca == 0) & (noturno_col == 0)
            & ~eh_fds & ~eh_feriado & ~saida_noturno
        )
        df["falta"] = dia_util_sem_trabalho.astype(int)

        # fds por dia_semana (garantia defensiva)
        if "dia_semana" in df.columns:
            df.loc[df["dia_semana"].isin(["Sabado", "Domingo"]), "falta"] = 0

        # ── Enfermeiros: forçar zeros nas colunas não aplicáveis ─────────────
        # (presenca, diurno_h, noturno_h, domingo_h já calculados por
        #  _calcular_horas_enfermeiro antes deste método)
        if "grupo" in df.columns:
            enf = df["grupo"] == "Enfermeiro"
            df.loc[enf, "falta"]             = 0
            df.loc[enf, "subsidio_refeicao"] = 0
            df.loc[enf, "baixa"]             = 0
            df.loc[enf, "ferias"]            = 0

        if "feriado" in df.columns:
            f = _f("feriado").apply(lambda x: round(float(x), 2))
            df["feriado"] = f.where(f >= 0.1, 0.0)
        if "ferias" in df.columns:
            f = _f("ferias")
            df["ferias"] = f.where(f >= 0.1, 0).astype(int)
        if "noturno" in df.columns:
            df["noturno"] = _f("noturno").apply(lambda x: round(float(x), 2))
        if "baixa" in df.columns:
            df["baixa"] = _f("baixa").astype(int).clip(0, 1)

        return df

    def _split_numero_nome(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Separa o campo 'nome' no formato 'NUM - Nome Completo'
        em duas colunas: 'numero' e 'nome'.
        Chamado logo após _aplicar_regras_negocio, antes de qualquer outro passo.
        """
        df = df.copy()
        if "numero" in df.columns:
            return df  # já separado
        if "nome" not in df.columns:
            df["numero"] = ""
            return df
        split = df["nome"].astype(str).str.split(r" - ", n=1, expand=True)
        if split.shape[1] == 2:
            df.insert(df.columns.get_loc("nome"), "numero", split[0].str.strip())
            df["nome"] = split[1].str.strip()
        else:
            df.insert(df.columns.get_loc("nome"), "numero", "")
        return df

    def _juntar_erros(self, mensal: pd.DataFrame, erros_total: list) -> pd.DataFrame:
        """
        Associa erros de picagem ao resumo mensal comparando pelo NÚMERO
        (parte antes de ' - ' no campo nome, que ainda não foi splitado).

        Chamado ANTES de _transformar_colunas.
        """
        mensal = mensal.copy()
        mensal["erros_picagem"] = ""
        if not erros_total:
            return mensal
        try:
            df_erros = pd.concat(erros_total, ignore_index=True)
            df_erros = self._filtrar_erros_noturno(df_erros, mensal)
            if df_erros.empty:
                return mensal

            # numero já é coluna separada após _split_numero_nome
            def _extrair_numero(nome_completo: str) -> str:
                partes = str(nome_completo).split(" - ", 1)
                return partes[0].strip()

            for _, err in df_erros.iterrows():
                data_e   = str(err.get("data", "")).strip()
                nome_e   = str(err.get("nome", "")).strip()
                numero_e = _extrair_numero(nome_e)
                msg      = str(err.get("erro", "")).strip()

                mask = (
                    mensal["data"].astype(str).str.strip() == data_e
                ) & (
                    mensal["numero"].astype(str).str.strip() == numero_e
                )
                if mask.any():
                    idx = mensal[mask].index[0]
                    atual = mensal.at[idx, "erros_picagem"]
                    mensal.at[idx, "erros_picagem"] = (
                        f"{atual}; {msg}" if atual else msg
                    )
                else:
                    logger.debug(
                        f"Erro nao associado: data={data_e} numero={numero_e} msg={msg}"
                    )

            pass  # numero ja e coluna propria

        except Exception as e:
            logger.warning(f"Erro ao juntar erros: {e}", exc_info=True)
        return mensal


    @staticmethod
    def _classificar_grupo(df: pd.DataFrame) -> pd.DataFrame:
        """Marca cada linha como 'AAD' ou 'Enfermeiro' pelo número (>=500 = Enfermeiro)."""
        df = df.copy()
        def _grupo(num_str):
            try:
                return "Enfermeiro" if int(str(num_str).strip()) >= 500 else "AAD"
            except (ValueError, TypeError):
                return "AAD"
        df["grupo"] = df["numero"].apply(_grupo)
        return df


    def _calcular_horas_enfermeiro(self, df: pd.DataFrame, feriados: dict) -> pd.DataFrame:
        """
        Para enfermeiros (grupo == 'Enfermeiro') calcula:
          presenca   — horas totais entre picagens (diurno 08-21 + noturno 21-08)
          diurno_h   — horas entre 08:00 e 21:00
          noturno_h  — horas entre 21:00 e 08:00 (dia seguinte)
          domingo_h  — horas em domingo ou feriado (sobrepõe-se ao diurno/noturno)
        Regras:
          - sem falta, sem subsidio_refeicao, sem baixa, sem ferias
          - janela diurna:  08h–21h
          - janela noturna: 21h–08h
          - domingo/feriado: todas as horas desse dia, independente do turno
        """
        import datetime
        df = df.copy()
        p  = self._parse_hora

        # garantir colunas
        for col in ("diurno_h", "noturno_h", "domingo_h"):
            if col not in df.columns:
                df[col] = 0.0

        enf_mask = df["grupo"] == "Enfermeiro"
        if not enf_mask.any():
            return df

        DIURNO_INI = datetime.time(8,  0)
        DIURNO_FIM = datetime.time(21, 0)

        def _minutos_em_janela(dt_e: "pd.Timestamp", dt_s: "pd.Timestamp",
                               ini: datetime.time, fim: datetime.time) -> float:
            """Minutos do intervalo [dt_e, dt_s[ que caem dentro de [ini, fim[ de cada dia."""
            total = 0.0
            d = dt_e.date()
            while d <= dt_s.date():
                j_ini = pd.Timestamp.combine(d, ini)
                j_fim = pd.Timestamp.combine(d, fim)
                overlap_ini = max(dt_e, j_ini)
                overlap_fim = min(dt_s, j_fim)
                if overlap_fim > overlap_ini:
                    total += (overlap_fim - overlap_ini).total_seconds() / 60
                d += datetime.timedelta(days=1)
            return total

        datas_ser = pd.to_datetime(df["data"], errors="coerce")

        for idx in df.index[enf_mask]:
            row    = df.loc[idx]
            data_p = datas_ser.loc[idx]
            if pd.isna(data_p):
                continue

            # recolher picagens válidas do dia
            dt_e = dt_s = None
            for ce, cs in [("e1","s1"), ("e2","s2")]:
                ev = str(row.get(ce, "")).strip().upper()
                sv = str(row.get(cs, "")).strip().upper()
                if ev.startswith("S") or sv.startswith("E"):
                    continue
                e_h = p(row.get(ce))
                s_h = p(row.get(cs))
                if e_h is None or s_h is None:
                    continue
                # construir timestamps — saída pode ser dia seguinte
                candidate_e = pd.Timestamp.combine(data_p.date(), e_h.time())
                candidate_s = pd.Timestamp.combine(data_p.date(), s_h.time())
                if candidate_s <= candidate_e:
                    candidate_s += datetime.timedelta(days=1)
                if dt_e is None or candidate_e < dt_e:
                    dt_e = candidate_e
                if dt_s is None or candidate_s > dt_s:
                    dt_s = candidate_s

            if dt_e is None or dt_s is None or dt_s <= dt_e:
                # sem picagens — zeros, sem falta
                df.at[idx, "presenca"]         = 0.0
                df.at[idx, "falta"]            = 0
                df.at[idx, "subsidio_refeicao"]= 0
                df.at[idx, "baixa"]            = 0
                df.at[idx, "ferias"]           = 0
                df.at[idx, "diurno_h"]         = 0.0
                df.at[idx, "noturno_h"]        = 0.0
                df.at[idx, "domingo_h"]        = 0.0
                continue

            total_h = round((dt_s - dt_e).total_seconds() / 3600, 2)

            # diurno: 08-21
            min_diurno  = _minutos_em_janela(dt_e, dt_s, DIURNO_INI, DIURNO_FIM)
            h_diurno    = round(min_diurno / 60, 2)
            h_noturno   = round(total_h - h_diurno, 2)

            # domingo/feriado: horas do dia de entrada que é dom/feriado
            eh_dom_fer  = (data_p.weekday() == 6 or
                           data_p.date() in feriados)
            h_domfer    = round(total_h, 2) if eh_dom_fer else 0.0

            df.at[idx, "presenca"]          = total_h
            df.at[idx, "diurno_h"]          = h_diurno
            df.at[idx, "noturno_h"]         = h_noturno
            df.at[idx, "domingo_h"]         = h_domfer
            df.at[idx, "falta"]             = 0
            df.at[idx, "subsidio_refeicao"] = 0
            df.at[idx, "baixa"]             = 0
            df.at[idx, "ferias"]            = 0

        return df

    def _adicionar_totais(self, df):
        if df is None or df.empty:
            return df
        cols_num = ["presenca", "falta", "feriado", "ferias",
                    "noturno", "baixa", "subsidio_refeicao"]
        partes = []
        for (numero, nome), grupo in df.groupby(["numero", "nome"], sort=True):
            partes.append(grupo)
            linha = {"data": "TOTAL", "numero": numero, "nome": nome,
                     "e1": "", "s1": "", "e2": "", "s2": "",
                     "observacoes_dl": "", "observacoes_cs": ""}
            for col in cols_num:
                if col in grupo.columns:
                    linha[col] = round(float(
                        pd.to_numeric(grupo[col], errors="coerce").fillna(0).sum()
                    ), 2)
            partes.append(pd.DataFrame([linha]))
        return pd.concat(partes, ignore_index=True)

    def _gerar_resumo(self, mensal):
        if mensal is None or mensal.empty:
            return pd.DataFrame()
        df = mensal[mensal["data"] != "TOTAL"]
        resumo = []
        for (numero, nome), grupo in df.groupby(["numero", "nome"]):
            presenca = pd.to_numeric(grupo["presenca"], errors="coerce").fillna(0)
            noturno  = pd.to_numeric(
                grupo.get("noturno", pd.Series([0]*len(grupo), index=grupo.index)),
                errors="coerce").fillna(0)
            resumo.append({
                "numero":          numero,
                "nome":            nome,
                "dias_8h_ou_mais": int((presenca >= 8).sum()),
                "total_horas":     round(float(presenca.sum()), 2),
                "horas_noturno":   round(float(noturno.sum()), 2),
            })
        return pd.DataFrame(resumo).sort_values("nome")

    def _filtrar_erros_noturno(self, df_erros, mensal):
        if df_erros is None or df_erros.empty:
            return df_erros
        try:
            data_min = pd.to_datetime(
                mensal[mensal["data"] != "TOTAL"]["data"], errors="coerce").min()
            if pd.isna(data_min):
                return df_erros
            data_min_str = data_min.strftime("%Y-%m-%d")
        except Exception:
            return df_erros
        mensal_1dia = mensal[mensal["data"].astype(str).str.startswith(data_min_str)]
        noturno_ok = set(
            mensal_1dia[
                pd.to_numeric(mensal_1dia.get("noturno",
                    pd.Series(dtype=float)), errors="coerce") > 0
            ]["nome"].astype(str).str.strip().str.upper()
        )
        if not noturno_ok:
            return df_erros
        mask = (
            df_erros["data"].astype(str).str.startswith(data_min_str) &
            df_erros["nome"].astype(str).str.strip().str.upper().isin(noturno_ok)
        )
        return df_erros[~mask].reset_index(drop=True)

    def _validar_es_trocados(self, df):
        erros = []
        p = self._parse_hora

        df_ord = df.copy()
        df_ord["_data_p"] = pd.to_datetime(df_ord["data"], errors="coerce")
        df_ord = df_ord.sort_values(["nome", "_data_p"])

        for _, row in df_ord.iterrows():
            data = row.get("data")
            nome = row.get("nome")
            e1, s1, e2, s2 = row.get("e1"), row.get("s1"), row.get("e2"), row.get("s2")

            for col in ["s1", "s2"]:
                if str(row.get(col, "")).strip().startswith("E"):
                    erros.append({"data": data, "nome": nome,
                                  "e1": e1, "s1": s1, "e2": e2, "s2": s2,
                                  "erro": f"E em coluna {col}"})
            for col in ["e1", "e2"]:
                if str(row.get(col, "")).strip().startswith("S"):
                    erros.append({"data": data, "nome": nome,
                                  "e1": e1, "s1": s1, "e2": e2, "s2": s2,
                                  "erro": f"S em coluna {col}"})

        for nome, grupo in df_ord.groupby("nome", sort=False):
            grupo = grupo.sort_values("_data_p").reset_index(drop=True)
            for pos in range(len(grupo) - 1):
                row      = grupo.iloc[pos]
                row_next = grupo.iloc[pos + 1]
                e1_p     = p(row.get("e1"))
                s1_p     = p(row.get("s1"))
                e1_str   = str(row.get("e1", "")).strip().upper()
                data_p   = row.get("_data_p")
                data_next= row_next.get("_data_p")

                if (e1_p is not None and not e1_str.startswith("S") and
                        e1_p.hour >= 18 and s1_p is None):
                    if (not pd.isna(data_next) and not pd.isna(data_p) and
                            data_next.date() == data_p.date() + pd.Timedelta(days=1)):
                        s1_next = p(row_next.get("s1"))
                        e1_next = str(row_next.get("e1", "")).strip().upper()
                        if s1_next is None and (e1_next == "" or e1_next.startswith("E")):
                            erros.append({
                                "data": row_next.get("data"),
                                "nome": nome,
                                "e1":  row_next.get("e1"),
                                "s1":  row_next.get("s1"),
                                "e2":  row_next.get("e2"),
                                "s2":  row_next.get("s2"),
                                "erro": "Falta saida - dia sem picagem apos entrada nocturna"
                            })

        return pd.DataFrame(erros)
