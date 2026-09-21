# Security Policy

## Gestão de Segredos

- Nunca versionar `.streamlit/secrets.toml`
- Todas as credenciais devem estar em `st.secrets` (ou variáveis de ambiente)
- Não usar senhas hardcoded em código

## Controles implementados

- `src/config.py` centraliza leitura e validação de segredos
- `src/auth_service.py` usa hash PBKDF2 para autenticação
- `src/services/email_service.py` usa SMTP com segredo externo
- `.gitignore` bloqueia banco local e artefatos sensíveis

## Boas práticas operacionais

- Rotacionar senha de app SMTP periodicamente
- Revisar permissões de usuários por perfil (admin/qualidade/operador)
- Executar testes e validações antes de deploy
