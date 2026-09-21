"""Página de anomalias com 5W1H e prazos."""

from datetime import date, datetime
import streamlit as st

from src.config import get_settings
from src.services.anomalia_service import AnomaliaService
from src.services.email_service import EmailService
from src.services.relatorio_service import RelatorioService
from src.storage.sqlite_repository import SQLiteRepository


def render() -> None:
    """Renderiza abertura/edição de anomalias e histórico."""
    st.header("⚠️ Anomalias")
    settings = get_settings()
    repo = SQLiteRepository(settings.db_path)
    repo.init_schema()
    service = AnomaliaService(repo)

    with st.form("abrir_anomalia"):
        machine = st.text_input("Máquina")
        responsible_email = st.text_input("E-mail responsável")
        problem = st.text_area("Problema")
        due_date = st.date_input("Vencimento", value=date.today())
        st.markdown("### 5W1H")
        details = {
            "what": st.text_input("What"),
            "why": st.text_input("Why"),
            "where": st.text_input("Where"),
            "when": st.text_input("When"),
            "who": st.text_input("Who"),
            "how": st.text_input("How"),
        }
        submit = st.form_submit_button("Salvar ocorrência")

    if submit and machine and problem:
        occurrence_id = service.abrir(
            {
                "created_at": datetime.utcnow().isoformat(),
                "opened_by": st.session_state.get("username", "sistema"),
                "responsible_email": responsible_email,
                "machine": machine,
                "problem": problem,
                "status": "Pendente Ação Corretiva",
                "due_date": due_date.isoformat(),
                "details": details,
            }
        )

        st.success(f"Ocorrência {occurrence_id} criada")

        if settings.mail and responsible_email:
            try:
                EmailService(settings.mail).send_email(
                    responsible_email,
                    f"[ARIAM] Nova ocorrência {occurrence_id}",
                    f"Ocorrência {occurrence_id} aberta para máquina {machine}.\n\nProblema: {problem}",
                )
            except Exception as exc:  # noqa: BLE001
                st.warning(f"Ocorrência criada, mas o e-mail não foi enviado: {exc}")

        try:
            laudo = RelatorioService().gerar_relatorio_ocorrencia(
                f"Ocorrência {occurrence_id}",
                {
                    "Problema": problem,
                    "5W1H": "\n".join([f"{k}: {v or 'Não informado'}" for k, v in details.items()]),
                },
            )
            st.download_button(
                "Baixar laudo",
                data=laudo,
                file_name=f"laudo_{occurrence_id}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        except Exception as exc:  # noqa: BLE001
            st.warning(f"Ocorrência criada, mas o laudo não pôde ser gerado: {exc}")

    ocorrencias = repo.list_occurrences()
    if ocorrencias:
        st.dataframe(ocorrencias, use_container_width=True)
        vencidas = service.pendentes_vencidas(date.today())
        if vencidas:
            st.warning(f"Existem {len(vencidas)} ocorrências vencidas.")
