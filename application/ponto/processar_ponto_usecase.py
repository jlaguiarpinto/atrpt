# application/ponto/processar_ponto_usecase.py
import logging
import pandas as pd # type: ignore
from domain.secretaria.ponto_processor import PontoProcessor # type: ignore

logger = logging.getLogger(__name__)


class ProcessarPontoUseCase:

    _DIAS_PT = ["Segunda", "Terca", "Quarta", "Quinta", "Sexta", "Sabado", "Domingo"]

    # feriados nacionais portugueses fixos (mês, dia) → descrição
    _FERIADOS_FIXOS = {
        (1,  1):  "Ano Novo",
        (4,  25): "Dia da Liberdade",
        (5,  1):  "Dia do Trabalhador",
        (6,  10): "Dia de Portugal",
        (8,  15): "Assunção de Nossa Senhora",
        (10, 5):  "Implantação da República",
        (11, 1):  "Dia de Todos os Santos",
        (12, 1):  "Restauração da Independência",
        (12, 8):  "Imaculada Conceição",
        (12, 25): "Natal",
    }

    def __init__(self):
        self.processor = PontoProcessor()

    def executar(self, repo, ctx, on_progress=None):
        """
        Pipeline de processamento de ponto:

        FASE 1 — Recolha dos ficheiros diários
          Para cada ficheiro diário:
            - limpar_registos: normaliza o Excel
            - _validar_es_trocados: detecta erros de picagem; guarda em erros_total
            - _merge_preservando_campos: acumula no mensal; actualiza só e1/s1/e2/s2

        FASE 2 — Cálculo (após todos os ficheiros lidos)
          DEBUG: pausa para inspecção antes de calcular
          - reset de todas as colunas calculadas a zero
          - _split_numero_nome: "42 - João Silva" → numero="42", nome="João Silva"
          - sort por numero, nome, data
          - _classificar_grupo: numero>=500 → Enfermeiro, resto → AAD
          - _adicionar_dia_semana_feriado
          - _juntar_erros: associa erros ao mensal por data+nome
          - _calcular_presenca: s-e para e1/s1 e e2/s2 (dias sem noturno)
          - _calcular_noturno: entrada>=17h30 sem saída → busca saída no dia seguinte;
              total de horas no dia de entrada; dia de saída marcado (_noturno_saida_flag)
          - _calcular_feriados_aad: presença em feriado → coluna feriado (só AAD)
          - _calcular_horas_enfermeiro: diurno_h / noturno_h / domingo_h
          - _calcular_falta_subref:
              AAD: falta=1 se dia útil sem trabalho; subref=1 se trabalhou (excl. dia saída noturna)
              Enfermeiro: nunca falta nem subref
          - _adicionar_totais, guardar
        """
        def log(msg):
            logger.info(msg)
            if on_progress:
                on_progress(msg)

        ficheiros = repo.listar_ficheiros_diarios()
        if not ficheiros:
            log("Sem ficheiros diarios.")
            return 0, None
        log(f"📂 {len(ficheiros)} ficheiros encontrados")

        mensal      = repo.ler_mensal()
        total       = 0
        erros_total = []

        # último dia do mês anterior (para turnos nocturnos que transitam)
        df_dia_anterior = None
        try:
            df_raw_ant = repo.ler_ultimo_dia_mes_anterior()
            if df_raw_ant is not None:
                df_dia_anterior = self.processor.limpar_registos(df_raw_ant)
                log("📅 Ultimo dia do mes anterior carregado")
        except Exception as e:
            logger.warning(f"Nao foi possivel ler mes anterior: {e}")

        # ── FASE 1: recolha ───────────────────────────────────────────────────
        for f in ficheiros:
            log(f"📄 {f.name}")
            try:
                df_raw   = repo.ler_excel(f)
                df_limpo = self.processor.limpar_registos(df_raw)
                df_erros = self._validar_es_trocados(df_limpo)
                log(f"   - {len(df_limpo)} registos, {len(df_erros)} erros")
                if not df_erros.empty:
                    erros_total.append(df_erros)
                mensal = self._merge_preservando_campos(mensal, df_limpo)
                total += 1
            except Exception as e:
                logger.error(f"Erro em {f.name}: {e}", exc_info=True)
                log(f"Erro em {f.name}: {e}")

        if mensal is None or mensal.empty:
            log("Sem dados validos.")
            return total, None

        # ── DEBUG: inspecção após recolha ─────────────────────────────────────
        _cols = [c for c in ["data", "nome", "e1", "s1", "e2", "s2"]
                 if c in mensal.columns]
        _dbg = mensal[_cols][mensal["data"].astype(str) != "TOTAL"].copy()
        _dbg["erro"] = ""
        if erros_total:
            _de = pd.concat(erros_total, ignore_index=True)
            _em = {}
            for _, _r in _de.iterrows():
                _k = (str(_r.get("data", "")).strip(), str(_r.get("nome", "")).strip())
                _v = str(_r.get("erro", "")).strip()
                _em[_k] = (_em.get(_k, "") + "; " + _v).strip("; ")
            _dbg["erro"] = _dbg.apply(
                lambda r: _em.get(
                    (str(r["data"]).strip(), str(r["nome"]).strip()), ""),
                axis=1)
        with pd.option_context("display.max_rows", None, "display.width", 220):
            print(_dbg.to_string(index=False))
        _n_err = int(_dbg["erro"].astype(bool).sum())
        _n_lin = len(_dbg)
        print(str(_n_lin) + " linhas | " + str(_n_err) + " com erros")

        # ── fim DEBUG ─────────────────────────────────────────────────────────

        # ── FASE 2: cálculo ───────────────────────────────────────────────────

        # garantir colunas de picagem e obs
        for col in ["e1", "s1", "e2", "s2", "data", "nome"]:
            if col not in mensal.columns:
                mensal[col] = None
        if "obs" not in mensal.columns:
            # migrar observacoes_dl / observacoes_cs → obs se existirem
            partes = []
            for _oc in ("observacoes_dl", "observacoes_cs"):
                if _oc in mensal.columns:
                    partes.append(mensal[_oc].fillna("").astype(str).str.strip())
            if partes:
                import functools
                mensal["obs"] = functools.reduce(
                    lambda a, b: a.where(b == "", a + " | " + b).where(a != "", b),
                    partes
                ).str.strip(" |")
                mensal = mensal.drop(columns=[c for c in ("observacoes_dl","observacoes_cs")
                                              if c in mensal.columns])
            else:
                mensal["obs"] = ""
        else:
            mensal["obs"] = mensal["obs"].fillna("")

        # resetar todas as colunas calculadas (evita acumulação em reprocessamentos)
        for col in ["falta", "ferias", "baixa", "subsidio_refeicao"]:
            mensal[col] = 0
        for col in ["presenca", "noturno", "feriado"]:
            mensal[col] = 0.0

        # split numero+nome + ordenação + grupo
        mensal = self._split_numero_nome(mensal)
        mensal = mensal.sort_values(["numero", "nome", "data"]).reset_index(drop=True)
        mensal = self._classificar_grupo(mensal)

        # dia_semana, feriado_desc
        mensal = self._adicionar_dia_semana_feriado(mensal)

        # erros de picagem
        mensal = self._juntar_erros(mensal, erros_total)

        # ── colunas de classificação temporárias ─────────────────────────────
        # Cada linha sabe o que é antes de qualquer cálculo.
        # Removidas no fim, antes de gravar.
        mensal = self._classificar_linhas(mensal, df_dia_anterior)

        # ── exportar classificação para diagnóstico ───────────────────────────
        try:
            _cols_class = (
                [c for c in ["data", "dia_semana", "numero", "nome", "e1", "s1", "e2", "s2"]
                 if c in mensal.columns] +
                [c for c in mensal.columns if c.startswith("_c_")] +
                (["erros_picagem"] if "erros_picagem" in mensal.columns else [])
            )
            _df_class = mensal[_cols_class][mensal["data"].astype(str) != "TOTAL"].copy()
            # renomear _c_* para nomes legíveis
            _rename = {
                "_c_enfermeiro":   "enfermeiro",
                "_c_noturno":      "noturno",
                "_c_noturno_saida":"noturno_saida",
                "_c_fds":          "fim_semana",
                "_c_feriado":      "feriado",
                "_c_erro":         "erro_picagem",
            }
            _df_class = _df_class.rename(columns={k: v for k, v in _rename.items()
                                                   if k in _df_class.columns})
            _path_class = repo.pasta_mes / "classificacao_debug.xlsx"
            _df_class.to_excel(_path_class, index=False)
            log(f"📋 Classificação gravada em: {_path_class.name}")
        except Exception as _ex:
            logger.warning(f"Nao foi possivel gravar classificacao_debug.xlsx: {_ex}")
        # ── fim exportar classificação ────────────────────────────────────────

        # ── cálculos em função das classificações ─────────────────────────────
        mensal = self._calcular_presenca(mensal)
        mensal = self._calcular_noturno_flags(mensal)
        mensal = self._calcular_feriados_aad(mensal)
        _anos = pd.to_datetime(mensal["data"], errors="coerce").dt.year.dropna().unique()
        _fer  = {}
        for _a in _anos:
            _fer.update(self._feriados_ano(int(_a)))
        mensal = self._calcular_horas_enfermeiro(mensal, _fer)
        mensal = self._calcular_falta_subref(mensal)

        # hext
        for _c in ("hext50", "hext75", "hext100"):
            if _c not in mensal.columns:
                mensal[_c] = 0

        colunas_finais = [
            "data", "dia_semana", "feriado_desc",
            "numero", "nome", "grupo",
            "e1", "s1", "e2", "s2",
            "presenca", "falta", "feriado", "ferias",
            "noturno", "baixa", "subsidio_refeicao",
            "diurno_h", "noturno_h", "domingo_h",
            "hext50", "hext75", "hext100",
            "erros_picagem", "obs",
        ]
        # remover todas as colunas temporárias (_c_* e outras)
        _tmp_cols = [c for c in mensal.columns
                     if c.startswith("_c_") or c in (
                         "_noturno_saida_flag", "_noturno_saida", "_noturno_subref",
                         "_c_tem_trabalho", "_c_limpar_erro",
                         "observacoes_dl", "observacoes_cs")]
        if _tmp_cols:
            mensal = mensal.drop(columns=_tmp_cols)
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

        n_erros = (mensal["erros_picagem"].astype(bool).sum()
                   if "erros_picagem" in mensal.columns else 0)
        log(f"{'⚠️ ' + str(n_erros) + ' erros de picagem' if n_erros else 'Sem erros de picagem'}")
        log(f"\n✔ {total} ficheiros processados")
        return total, output

    # ── merge preservando campos existentes ──────────────────────────────────
    # Chave: nome + data (número ignorado no cruzamento).
    # Linhas existentes: só e1/s1/e2/s2 actualizados se mudaram.
    # Linhas novas: splitadas em numero+nome e adicionadas.
    # ──────────────────────────────────────────────────────────────────────────
    _CAMPOS_PICAGEM    = ("e1", "s1", "e2", "s2")

    def _merge_preservando_campos(
        self,
        mensal: "pd.DataFrame | None",
        df_novo: "pd.DataFrame",
    ) -> "pd.DataFrame":
        """
        Merge do ficheiro diário (df_novo) com o acumulado (mensal).

        O campo 'nome' mantém-se SEMPRE no formato original "42 - João Silva"
        durante toda a fase de recolha. O split em 'numero'+'nome' só acontece
        no fim do pipeline, em _split_numero_nome.

        Chave de cruzamento: nome original (strip) + data.
          - Linha nova      → adicionada tal como vem do ficheiro.
          - Linha existente → só e1/s1/e2/s2 actualizados se mudaram;
                              todos os outros campos ficam inalterados.
        """
        def _data_str(raw) -> str:
            p = pd.to_datetime(raw, errors="coerce")
            return p.strftime("%Y-%m-%d") if not pd.isna(p) else str(raw).strip()

        if mensal is None or mensal.empty:
            return df_novo.copy()

        mensal  = mensal.copy()
        df_novo = df_novo.copy()

        # índice do mensal por nome_original||data (excluindo linhas TOTAL)
        mask_nao_total = mensal["data"].astype(str) != "TOTAL"
        idx_por_chave: dict[str, int] = {
            str(row["nome"]).strip() + "||" + _data_str(row["data"]): i
            for i, row in mensal[mask_nao_total].iterrows()
        }

        linhas_novas: list = []

        for _, row_novo in df_novo.iterrows():
            if str(row_novo.get("data", "")) == "TOTAL":
                continue

            nome_n = str(row_novo.get("nome", "")).strip()
            data_n = _data_str(row_novo.get("data"))
            chave  = nome_n + "||" + data_n

            if chave not in idx_por_chave:
                linhas_novas.append(row_novo)
                continue

            # linha existente — actualizar só e1/s1/e2/s2 se mudaram
            idx_men = idx_por_chave[chave]
            for campo in self._CAMPOS_PICAGEM:
                val_men  = str(mensal.at[idx_men, campo]
                               if campo in mensal.columns else "").strip()
                val_novo = str(row_novo.get(campo, "") or "").strip()
                if val_novo and val_novo != val_men:
                    logger.info(
                        f"Picagem actualizada — {nome_n} {data_n}: "
                        f"{campo} {val_men!r}->{val_novo!r}"
                    )
                    mensal.at[idx_men, campo] = val_novo

        if linhas_novas:
            mensal = pd.concat(
                [mensal, pd.DataFrame(linhas_novas)],
                ignore_index=True,
            )

        return mensal

    # ──────────────────────────────────────────────────────────────────────────

    def _calcular_presenca(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula horas de presença diurna usando as classificações _c_erro
        e o número de picagens válidas presentes (e1/s1/e2/s2).

        Regras por número de picagens e erro:

        4 picagens (e1 s1 e2 s2):
          - com ou sem erro → calcular (e1→s1) + (e2→s2); falta=0, subref=1
            (se há erro de picagem a sequência pode estar trocada mas há trabalho)

        3 picagens (qualquer combinação de 3 preenchidos):
          - com ou sem erro → calcular só os 2 primeiros registos cronológicos;
            falta=0, subref=1

        2 picagens:
          - sem erro → calcular normalmente (e1→s1 ou e2→s2 conforme disponível)
          - com erro → muito provavelmente trabalho noturno em dias sucessivos
            (saída matinal + entrada ao fim do dia); não é erro real;
            calcular o par disponível; falta=0, subref=1

        1 picagem:
          - provavelmente saída de turno noturno (já contada no dia anterior);
            não registar como erro; presença=0, sem falta, sem subref
            (o dia já foi tratado em _calcular_noturno_flags)

        0 picagens:
          - sem trabalho registado (falta ou folga — decidido em _calcular_falta_subref)
        """
        df   = df.copy()
        p    = self._parse_hora

        def _min(hora_p):
            """Converte hora parsed para minutos desde meia-noite."""
            if hora_p is None:
                return None
            return hora_p.hour * 60 + hora_p.minute

        def _dur_min(e_min, s_min):
            """Duração em minutos; None se inválido."""
            if e_min is None or s_min is None:
                return None
            d = s_min - e_min
            return d if 0 < d < 24 * 60 else None

        def _calcular_row(row):
            # recolher os 4 valores, filtrar os que têm hora válida
            campos = [("e1", row.get("e1")), ("s1", row.get("s1")),
                      ("e2", row.get("e2")), ("s2", row.get("s2"))]
            horas = []
            for col, val in campos:
                h = p(val)
                if h is not None:
                    horas.append((col, _min(h)))

            n = len(horas)
            tem_erro = bool(row.get("_c_erro", False))

            if n == 0:
                return 0.0, False, False   # presença, marcar_subref, limpar_erro

            if n == 1:
                # 1 picagem — provavelmente saída noturna já contada
                # não é erro; presença=0 aqui (tratada em _calcular_noturno_flags)
                return 0.0, False, True    # limpar_erro=True (não é erro real)

            if n == 2:
                # ordenar cronologicamente e calcular o par
                horas_ord = sorted(horas, key=lambda x: x[1])
                d = _dur_min(horas_ord[0][1], horas_ord[1][1])
                h_total = round(d / 60, 2) if d else 0.0
                # com erro de 2 picagens: trabalho noturno consecutivo — não é erro real
                return h_total, h_total > 0, tem_erro   # limpar_erro se tem_erro

            if n == 3:
                # ordenar e usar os 2 primeiros
                horas_ord = sorted(horas, key=lambda x: x[1])
                d = _dur_min(horas_ord[0][1], horas_ord[1][1])
                h_total = round(d / 60, 2) if d else 0.0
                return h_total, h_total > 0, False

            # n == 4: calcular (e1→s1) + (e2→s2) pela ordem das colunas
            # independentemente de haver erro — há 4 picagens, há trabalho
            total = 0.0
            for ce, cs in [("e1", "s1"), ("e2", "s2")]:
                ev = str(row.get(ce, "") or "").strip().upper()
                sv = str(row.get(cs, "") or "").strip().upper()
                if ev.startswith("S") or sv.startswith("E"):
                    continue
                e_m = _min(p(row.get(ce)))
                s_m = _min(p(row.get(cs)))
                d   = _dur_min(e_m, s_m)
                if d:
                    total += d
            h_total = round(total / 60, 2)
            return h_total, h_total > 0, False

        resultados = df.apply(_calcular_row, axis=1)
        df["presenca"]         = resultados.apply(lambda r: r[0])
        df["_c_tem_trabalho"]  = resultados.apply(lambda r: r[1])
        df["_c_limpar_erro"]   = resultados.apply(lambda r: r[2])

        # limpar erro em casos onde não é erro real (1 picagem, 2 picagens noturnas)
        if "erros_picagem" in df.columns:
            df.loc[df["_c_limpar_erro"], "erros_picagem"] = ""
            df.loc[df["_c_limpar_erro"], "_c_erro"]       = False

        return df

    # ── novos métodos de cálculo ─────────────────────────────────────────────

    def _classificar_linhas(self, df: pd.DataFrame, df_dia_anterior=None) -> pd.DataFrame:
        """
        Cria colunas temporárias de classificação (prefixo _c_):

          _c_enfermeiro  : bool  — True se numero >= 500
          _c_noturno     : bool  — True se entrada >= 17h30 e saída no dia seguinte
          _c_noturno_saida: bool — True se é o dia de saída de um turno nocturno
          _c_fds         : bool  — True se sábado ou domingo
          _c_feriado     : bool  — True se feriado nacional/local
          _c_erro        : bool  — True se erros_picagem não vazio

        Estas colunas são usadas por todos os métodos de cálculo e removidas
        antes de gravar o ficheiro final.
        """
        df = df.copy()
        p  = self._parse_hora

        # _c_enfermeiro
        df["_c_enfermeiro"] = (
            pd.to_numeric(df.get("numero", pd.Series(0, index=df.index)),
                          errors="coerce").fillna(0) >= 500
        )

        # _c_fds
        datas = pd.to_datetime(df["data"], errors="coerce")
        df["_c_fds"] = datas.dt.weekday >= 5

        # _c_feriado
        anos = datas.dt.year.dropna().unique()
        fer_map = {}
        for ano in anos:
            fer_map.update(self._feriados_ano(int(ano)))
        df["_c_feriado"] = datas.apply(
            lambda d: d.date() in fer_map if not pd.isna(d) else False)

        # _c_erro
        df["_c_erro"] = df.get("erros_picagem", pd.Series("", index=df.index)
                                ).astype(str).str.strip() != ""

        # _c_noturno e _c_noturno_saida — percorrer por pessoa
        df["_c_noturno"]      = False
        df["_c_noturno_saida"] = False

        # mapa do dia anterior (turnos que transitam do mês anterior)
        mapa_anterior = {}
        if df_dia_anterior is not None:
            for _, _ra in df_dia_anterior.iterrows():
                _n  = str(_ra.get("nome", "")).strip().upper()
                _e1 = p(_ra.get("e1", ""))
                if _e1 is not None and (_e1.hour > 17 or
                                        (_e1.hour == 17 and _e1.minute >= 30)):
                    mapa_anterior[_n] = _e1

        try:
            data_min = pd.to_datetime(
                df[df["data"].astype(str) != "TOTAL"]["data"],
                errors="coerce").min()
        except Exception:
            data_min = None

        for nome, grupo in df.groupby("nome", sort=False):
            grupo    = grupo.sort_values("data").copy()
            datas_g  = pd.to_datetime(grupo["data"], errors="coerce")
            idx_list = list(grupo.index)

            for pos, idx in enumerate(idx_list):
                row    = grupo.loc[idx]
                data_p = datas_g.loc[idx]
                if pd.isna(data_p):
                    continue

                e1_p   = p(row.get("e1"))
                e1_str = str(row.get("e1", "")).strip().upper()
                s1_p   = p(row.get("s1"))
                s1_str = str(row.get("s1", "")).strip().upper()

                # primeiro dia do mês: saída de turno anterior
                e_primeiro = (data_min is not None and
                              data_p.date() == data_min.date())
                if e_primeiro and s1_p is not None and (
                        e1_p is None or e1_str.startswith("S")):
                    nome_up = str(nome).strip().upper()
                    if nome_up in mapa_anterior:
                        df.at[idx, "_c_noturno_saida"] = True
                    continue

                # entrada >= 17h30
                if e1_p is None or e1_str.startswith("S"):
                    continue
                if e1_p.hour < 17 or (e1_p.hour == 17 and e1_p.minute < 30):
                    continue

                # confirmar que há saída no dia seguinte
                if pos + 1 < len(idx_list):
                    idx_next  = idx_list[pos + 1]
                    row_next  = grupo.loc[idx_next]
                    data_next = datas_g.loc[idx_next]
                    if (not pd.isna(data_next) and
                            data_next.date() == data_p.date() + pd.Timedelta(days=1)):
                        s1_c = p(row_next.get("s1"))
                        e1_c = str(row_next.get("e1", "")).strip().upper()
                        if s1_c is not None and (e1_c == "" or e1_c.startswith("S")):
                            df.at[idx,      "_c_noturno"]       = True
                            df.at[idx_next, "_c_noturno_saida"] = True
                            continue
                # sem saída encontrada — ainda noturno (saída em falta)
                df.at[idx, "_c_noturno"] = True

        return df

    def _calcular_noturno_flags(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula horas de noturno usando _c_noturno e _c_noturno_saida.

        Fórmula: (24*60 - min_entrada) + min_saída_dia_seguinte
          onde min_saída é a primeira picagem válida do dia de saída
          (pode estar em e1 com prefixo S, s1, etc.)

        As horas são somadas à presença já calculada para o dia de entrada
        (caso existam picagens diurnas antes do turno noturno nesse dia).
        """
        df  = df.copy()
        p   = self._parse_hora
        df["noturno"] = 0.0

        def _primeira_hora_dia(row) -> "int | None":
            """Primeira hora válida do dia (ignora prefixos E/S)."""
            for col in ["e1", "s1", "e2", "s2"]:
                h = p(row.get(col))
                if h is not None:
                    return h.hour * 60 + h.minute
            return None

        for nome, grupo in df.groupby("nome", sort=False):
            grupo    = grupo.sort_values("data").copy()
            datas_g  = pd.to_datetime(grupo["data"], errors="coerce")
            idx_list = list(grupo.index)

            for pos, idx in enumerate(idx_list):
                if not df.at[idx, "_c_noturno"]:
                    continue

                row  = grupo.loc[idx]
                e1_p = p(row.get("e1"))
                if e1_p is None:
                    continue

                min_e1   = e1_p.hour * 60 + e1_p.minute
                h_ate_mn = round((24 * 60 - min_e1) / 60, 2)   # entrada → 00:00

                # procurar primeira picagem no dia seguinte (a saída)
                h_saida_dia_seg = 0.0
                if pos + 1 < len(idx_list):
                    idx_next  = idx_list[pos + 1]
                    data_p    = datas_g.loc[idx]
                    data_next = datas_g.loc[idx_next]
                    if (not pd.isna(data_next) and not pd.isna(data_p) and
                            data_next.date() == data_p.date() + pd.Timedelta(days=1)):
                        min_saida = _primeira_hora_dia(grupo.loc[idx_next])
                        if min_saida is not None:
                            # 00:00 → saída
                            h_saida_dia_seg = round(min_saida / 60, 2)

                # total noturno = (entrada→00:00) + (00:00→saída)
                df.at[idx, "noturno"] = round(h_ate_mn + h_saida_dia_seg, 2)

        return df

    def _calcular_feriados_aad(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Usa _c_feriado e _c_enfermeiro.
        AAD em feriado: presença → feriado. Enfermeiro: intocado.
        """
        df = df.copy()
        feriado  = df.get("_c_feriado",    pd.Series(False, index=df.index)).fillna(False)
        enf      = df.get("_c_enfermeiro", pd.Series(False, index=df.index)).fillna(False)
        presenca = pd.to_numeric(df.get("presenca", 0), errors="coerce").fillna(0)
        transferir     = feriado & ~enf
        df["feriado"]  = presenca.where(transferir, 0.0).round(2)
        df["presenca"] = presenca.where(~transferir, 0.0).round(2)
        return df

    def _calcular_falta_subref(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Usa _c_enfermeiro, _c_fds, _c_feriado, _c_noturno_saida.
        AAD : falta=1 se dia útil sem trabalho; subref=1 se trabalhou e não saída-noturna.
        Enfermeiro: falta=0, subref=0 sempre.
        """
        df = df.copy()
        enf        = df.get("_c_enfermeiro",   pd.Series(False, index=df.index)).fillna(False)
        fds        = df.get("_c_fds",          pd.Series(False, index=df.index)).fillna(False)
        feriado    = df.get("_c_feriado",      pd.Series(False, index=df.index)).fillna(False)
        not_saida  = ~df.get("_c_noturno_saida", pd.Series(False, index=df.index)).fillna(False)
        presenca   = pd.to_numeric(df.get("presenca", 0), errors="coerce").fillna(0)
        noturno    = pd.to_numeric(df.get("noturno",  0), errors="coerce").fillna(0)
        # _c_tem_trabalho já inclui casos de erro com trabalho detectado
        tem_trab_calc = df.get("_c_tem_trabalho", pd.Series(False, index=df.index)).fillna(False)
        tem_trab   = (presenca > 0) | (noturno > 0) | tem_trab_calc
        aad        = ~enf

        df["falta"]             = (aad & ~fds & ~feriado & not_saida & ~tem_trab).astype(int)
        df["subsidio_refeicao"] = (aad & tem_trab & not_saida).astype(int)

        # Enfermeiro: zeros explícitos
        df.loc[enf, "falta"]             = 0
        df.loc[enf, "subsidio_refeicao"] = 0
        df.loc[enf, "baixa"]             = 0
        df.loc[enf, "ferias"]            = 0

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

    def _pascoa(self, ano: int):
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
        """Normalização final de tipos — feriados, falta e subref já calculados."""
        df = df.copy()
        def _f(col):
            if col not in df.columns:
                return pd.Series([0.0] * len(df), index=df.index)
            return pd.to_numeric(df[col], errors="coerce").fillna(0)
        for col in ("feriado", "noturno", "presenca"):
            if col in df.columns:
                v = _f(col).round(2)
                df[col] = v.where(v >= 0.01, 0.0)
        if "ferias" in df.columns:
            df["ferias"] = _f("ferias").clip(0).astype(int)
        if "baixa" in df.columns:
            df["baixa"] = _f("baixa").astype(int).clip(0, 1)
        return df

    def _split_numero_nome(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Separa o campo 'nome' no formato 'NUM - Nome Completo'
        em duas colunas: 'numero' e 'nome'.
        Chamado uma única vez no fim da recolha, antes de ordenar e classificar.
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
        Associa erros de picagem ao resumo mensal.

        Chamado ANTES de _split_numero_nome — o mensal ainda tem o nome
        no formato original "42 - João Silva". O cruzamento é feito pelo
        nome completo (data + nome original), que existe em ambos os lados.
        Normaliza datas para "YYYY-MM-DD" antes de comparar.
        """
        mensal = mensal.copy()
        mensal["erros_picagem"] = ""
        if not erros_total:
            return mensal

        def _norm_data(val) -> str:
            """Normaliza qualquer representação de data para YYYY-MM-DD."""
            try:
                ts = pd.to_datetime(val, errors="coerce")
                return ts.strftime("%Y-%m-%d") if not pd.isna(ts) else str(val).strip()
            except Exception:
                return str(val).strip()

        try:
            df_erros = pd.concat(erros_total, ignore_index=True)
            df_erros = self._filtrar_erros_noturno(df_erros, mensal)
            if df_erros.empty:
                return mensal

            # normalizar datas do mensal uma vez só
            mensal_data_norm = mensal["data"].apply(_norm_data)

            n_ok = 0
            n_nok = 0
            for _, err in df_erros.iterrows():
                data_e = _norm_data(err.get("data", ""))
                nome_e = str(err.get("nome", "")).strip()
                msg    = str(err.get("erro", "")).strip()

                # cruzar por data normalizada + nome completo
                mask = (mensal_data_norm == data_e) & (
                    mensal["nome"].astype(str).str.strip() == nome_e
                )
                if mask.any():
                    idx   = mensal[mask].index[0]
                    atual = str(mensal.at[idx, "erros_picagem"] or "").strip()
                    mensal.at[idx, "erros_picagem"] = (
                        f"{atual}; {msg}" if atual else msg
                    )
                    n_ok += 1
                else:
                    logger.warning(
                        f"Erro nao associado: data={data_e!r} nome={nome_e!r} msg={msg!r}"
                    )
                    n_nok += 1

            logger.info(f"_juntar_erros: {n_ok} associados, {n_nok} nao associados")

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
                     "e1": "", "s1": "", "e2": "", "s2": "", "obs": ""}
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
        """
        Detecta erros de picagem:
          1. Letra errada na coluna: E em coluna S ou S em coluna E
          2. s2 preenchido sem e2  (e1-s1-?-s2 — saída sem entrada no 2º turno)
          3. e2 preenchido sem s2 + dia seguinte tem e1
             (e1-s1-e2-? — entrada sem saída, turno ficou aberto)
          4. Entrada nocturna (e1>=18h) sem s1 + dia seguinte sem picagem
             (caso já existente, mantido)
        """
        erros = []
        p = self._parse_hora

        def _vazio(val):
            """True se a picagem está em branco ou é nula."""
            return str(val or "").strip() == ""

        def _tem_hora(val):
            return p(val) is not None

        df_ord = df.copy()
        df_ord["_data_p"] = pd.to_datetime(df_ord["data"], errors="coerce")
        df_ord = df_ord.sort_values(["nome", "_data_p"])

        # ── caso 1: letra errada na coluna ────────────────────────────────────
        for _, row in df_ord.iterrows():
            data = row.get("data")
            nome = row.get("nome")
            e1, s1, e2, s2 = row.get("e1"), row.get("s1"), row.get("e2"), row.get("s2")

            for col in ["s1", "s2"]:
                if str(row.get(col, "")).strip().upper().startswith("E"):
                    erros.append({"data": data, "nome": nome,
                                  "e1": e1, "s1": s1, "e2": e2, "s2": s2,
                                  "erro": f"E em coluna {col}"})
            for col in ["e1", "e2"]:
                if str(row.get(col, "")).strip().upper().startswith("S"):
                    erros.append({"data": data, "nome": nome,
                                  "e1": e1, "s1": s1, "e2": e2, "s2": s2,
                                  "erro": f"S em coluna {col}"})

            # ── caso 2: s2 preenchido sem e2 ─────────────────────────────────
            # sequência: e1-s1-??-s2  (saída sem entrada no 2º turno)
            if _tem_hora(s2) and _vazio(e2):
                erros.append({"data": data, "nome": nome,
                              "e1": e1, "s1": s1, "e2": e2, "s2": s2,
                              "erro": "S2 sem E2 — saida do 2º turno sem entrada"})

            # ── caso 3: e2 preenchido sem s2 ─────────────────────────────────
            # sequência: e1-s1-e2-?  (entrada no 2º turno sem saída)
            # detectado por linha — não depende do dia seguinte
            _e2_str = str(e2 or "").strip().upper()
            _e2_p   = p(e2)
            if _e2_p is not None and not _e2_str.startswith("S") and _vazio(s2):
                erros.append({"data": data, "nome": nome,
                              "e1": e1, "s1": s1, "e2": e2, "s2": s2,
                              "erro": "E2 sem S2 — entrada do 2º turno sem saida"})

        # ── casos 3 e 4: análise entre dias consecutivos ──────────────────────
        for nome, grupo in df_ord.groupby("nome", sort=False):
            grupo = grupo.sort_values("_data_p").reset_index(drop=True)
            for pos in range(len(grupo) - 1):
                row      = grupo.iloc[pos]
                row_next = grupo.iloc[pos + 1]
                data_p   = row.get("_data_p")
                data_next= row_next.get("_data_p")

                if pd.isna(data_p) or pd.isna(data_next):
                    continue
                dias_consecutivos = (
                    data_next.date() == data_p.date() + pd.Timedelta(days=1)
                )

                e1_str = str(row.get("e1", "")).strip().upper()
                e2_str = str(row.get("e2", "")).strip().upper()
                s2_str = str(row.get("s2", "")).strip().upper()

                e1_p = p(row.get("e1"))
                s1_p = p(row.get("s1"))
                e2_p = p(row.get("e2"))
                s2_p = p(row.get("s2"))

                # ── caso 4: entrada nocturna (e1>=18h) sem s1 ────────────────
                # (lógica original mantida)
                if (e1_p is not None
                        and not e1_str.startswith("S")
                        and e1_p.hour >= 18
                        and s1_p is None
                        and dias_consecutivos):
                    s1_next = p(row_next.get("s1"))
                    e1_next = str(row_next.get("e1", "")).strip().upper()
                    if s1_next is None and (e1_next == "" or e1_next.startswith("E")):
                        erros.append({
                            "data": row_next.get("data"),
                            "nome": nome,
                            "e1": row_next.get("e1"), "s1": row_next.get("s1"),
                            "e2": row_next.get("e2"), "s2": row_next.get("s2"),
                            "erro": "Falta saida — dia sem picagem apos entrada nocturna"
                        })

        return pd.DataFrame(erros)
