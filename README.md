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

## Evidências fotográficas: câmera ou arquivo

Nas inspeções, escolha **Origem da evidência fotográfica**:
**Enviar arquivo** (JPG/JPEG/PNG; também WebP no app modular) ou
**Tirar foto / Usar câmera**. Os dois controles ficam visíveis, mas somente
a origem selecionada é anexada; não há reaproveitamento da outra origem
quando a selecionada está vazia. Para reutilizar uma origem, confira a imagem
que ainda estiver visível nela ou remova/substitua essa imagem.

Na tela legada (`streamlit run app_tablet.py`), a seção
**4 Anexo de Evidência Fotográfica & Conclusão** inclui o botão
**Conferir prévia da foto**: ele envia os campos para conferência sem salvar
a inspeção. Depois clique em **Salvar Inspeção e Gerar Laudo Técnico**.
Fotos de câmera e arquivo passam pela mesma validação (até 5 MiB por foto),
correção de orientação e conversão para PNG. São salvas em `fotos_inspecoes/`,
referenciadas em `Log_Inspecoes_Semanais.xlsx` e incorporadas ao laudo Word.
Mantenha a pasta de fotos junto à planilha para gerar laudos posteriormente.
No app modular (`app.py`), preserva-se o fluxo existente: vários arquivos ou
uma captura, prévia imediata e registro dos nomes no SQLite; esse fluxo
**não armazena os bytes nem gera laudo fotográfico**.

### Acesso à câmera e roteiro manual (Android/desktop)

A captura usa o componente nativo do Streamlit e depende de câmera disponível,
navegador compatível e permissão do navegador e do sistema operacional.
Abra o aplicativo por **HTTPS** com certificado válido; `localhost` só vale
no próprio dispositivo que executa o navegador. Um endereço HTTP por IP da
rede (por exemplo, o servidor acessado do tablet) normalmente não permite
câmera. Em páginas incorporadas, o site hospedeiro também precisa permitir
o uso da câmera. A câmera frontal/traseira disponível depende do navegador;
não há garantia de seleção automática da traseira.

1. No tablet Android, abra a seção de evidências, selecione **Tirar foto /
   Usar câmera**, ative a câmera e permita o acesso solicitado pelo navegador.
2. Capture uma foto, confira a imagem e, no legado, clique em **Conferir prévia
   da foto**. Verifique que os demais campos preenchidos continuam intactos.
3. Salve a inspeção, selecione seu ID no histórico e baixe o laudo Word.
   Confira se a foto está correta e orientada.
4. Troque para **Enviar arquivo**, selecione um JPG/PNG diferente, confira a
   prévia e salve. Verifique que o laudo usa o arquivo, não a captura anterior.
5. Troque para uma origem sem imagem: confirme a indicação de ausência de foto,
   sem reaproveitar a outra origem.
6. Negue a permissão da câmera: confira a orientação na tela e use **Enviar
   arquivo**. Para tentar novamente, libere a câmera nas permissões do site e
   do Android, feche aplicativos que a estejam usando e recarregue a página.
   Repita em desktop com webcam (ou sem câmera, verificando a alternativa).

Testes automatizados simulam os bytes e o formulário; não substituem este
roteiro em hardware real nem validam permissões de câmera do navegador.

## Migração Excel -> SQLite

```bash
python scripts/migrate_excel_to_sqlite.py
```
