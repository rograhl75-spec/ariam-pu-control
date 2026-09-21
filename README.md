# ARIAM PU Control

Aplicação Streamlit para controle de produção PU com arquitetura modular, persistência SQLite e segurança via `st.secrets`.

## Principais melhorias aplicadas

- Segurança: remoção de segredo hardcoded e configuração sensível centralizada em `st.secrets`
- Persistência: repositório abstrato + implementação SQLite
- Arquitetura: serviços separados por domínio e páginas modulares
- Funcional: produção, pesagem, reatividade, térmico, inspeções e anomalias com 5W1H
- Qualidade: testes para cálculos, validações e e-mail

## Estrutura

- `app.py`: novo entry point
- `app_tablet.py`: legado (depreciado)
- `src/config.py`: configuração segura
- `src/storage/sqlite_repository.py`: persistência principal
- `src/services/*`: serviços de domínio
- `src/pages/*`: páginas Streamlit
- `scripts/migrate_excel_to_sqlite.py`: migração de logs legados

## Configuração

1. Copie `.streamlit/secrets.example.toml` para `.streamlit/secrets.toml`
2. Gere hashes de senha:

```bash
python -c "from src.auth_service import AuthService; print(AuthService.hash_password('SUA_SENHA'))"
```

3. Preencha credenciais e hashes em `.streamlit/secrets.toml`
4. Instale dependências:

```bash
pip install -r requirements.txt
```

## Execução

```bash
streamlit run app.py
```

## Testes

```bash
pytest -q
```

## Migração Excel -> SQLite

```bash
python scripts/migrate_excel_to_sqlite.py
```
