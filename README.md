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
**Tirar foto com câmera traseira**. Somente a origem selecionada é anexada;
o upload fica desabilitado enquanto a câmera é a origem ativa, mas seus arquivos
são mantidos ao alternar. Ao sair da origem câmera, a captura é descartada:
ao voltar, tire uma nova foto. Uma nova tentativa de captura ou troca de câmera
também descarta a captura anterior, mesmo se a tentativa falhar.

Na tela legada (`streamlit run app_tablet.py`), a seção
**4 Anexo de Evidência Fotográfica & Conclusão** inclui o botão
**Conferir prévia da foto** (sem salvar a inspeção). Os campos desta seção
são reativos, sem formulário em lote, para preservar as descrições e permitir
troca imediata da origem. A prévia aparece automaticamente após a captura.
Depois clique em **Salvar Inspeção e Gerar Laudo Técnico**.
Fotos de câmera e arquivo passam pela mesma validação (até 5 MiB por foto),
correção de orientação e conversão para PNG. São salvas em `fotos_inspecoes/`,
referenciadas em `Log_Inspecoes_Semanais.xlsx` e incorporadas ao laudo Word.
Mantenha a pasta de fotos junto à planilha para gerar laudos posteriormente.
No app modular (`app.py`), preserva-se o fluxo existente: vários arquivos ou
uma captura, prévia imediata e registro dos nomes no SQLite; esse fluxo
**não armazena os bytes nem gera laudo fotográfico**.

### Acesso à câmera e roteiro manual (Android/desktop)

A aplicação fixa **Streamlit 1.39.0**. Nessa versão, `st.camera_input` não
expõe `facingMode` nem seletor de dispositivo (assinatura conferida no pacote
instalado). Por isso, `ui/rear_camera/` implementa um componente local, registrado
por `streamlit.components.v1.declare_component`. Ele usa o
[protocolo oficial de componentes v1](https://github.com/streamlit/streamlit/blob/1.39.0/component-lib/src/streamlit.ts)
para devolver JPEG em base64 ao Python, que valida os bytes pelo mesmo pipeline
do upload. Não há bibliotecas JavaScript remotas nem novos serviços externos.

A câmera **só abre após tocar no botão**, solicitando
`getUserMedia({audio: false, video: {facingMode: {ideal: "environment"}}})`.
Quando a enumeração é permitida, um seletor lista as câmeras disponíveis e
abre a escolhida com `deviceId` exato. Não há detecção por user-agent.
O navegador pode ignorar a preferência ou não informar a direção: nesse caso
a tela informa **câmera traseira não confirmada**; confira o enquadramento e
selecione outra câmera, se disponível, ou envie um arquivo. Uma webcam desktop
pode ser usada sem ser apresentada como câmera traseira.

Depende de câmera disponível, navegador compatível e permissão do navegador e do sistema operacional.
Abra o aplicativo por **HTTPS** com certificado válido; `localhost` só vale
no próprio dispositivo que executa o navegador. Um endereço HTTP por IP da
rede (por exemplo, o servidor acessado do tablet) normalmente não permite
câmera. Em páginas incorporadas, o site hospedeiro também precisa permitir
o uso da câmera. Nenhum componente consegue garantir uma câmera traseira
inexistente ou bloqueada. Os tracks são encerrados ao capturar, cancelar,
trocar câmera/origem, ocultar a página ou sair dela; uma permissão que termine
de abrir após cancelamento também tem seu stream encerrado.

1. No tablet Android com câmera traseira, acesse por HTTPS, preencha descrições
   e selecione **Tirar foto com câmera traseira**. Confirme que a câmera não
   abre antes de tocar no botão de mesmo nome. Toque e permita o acesso.
   Aponte para um equipamento e confirme que a imagem é da câmera traseira,
   não uma selfie. Se houver seletor, troque entre frontal/traseira e confira
   a imagem e o desligamento da câmera anterior. Teste tablet em retrato e paisagem.
2. Capture uma foto, confira a imagem e, no legado, clique em **Conferir prévia
   da foto**. Verifique que os demais campos preenchidos continuam intactos.
3. Salve a inspeção, selecione seu ID no histórico e baixe o laudo Word.
   Confira se a foto está correta e orientada.
4. Troque para **Enviar arquivo**, selecione um JPG/PNG diferente, confira a
   prévia e salve. Verifique que o laudo usa o arquivo, não a captura anterior.
5. Volte para a origem câmera: confirme que a captura antiga foi removida e
   não é salva silenciosamente. Capture novamente, remova a foto e teste
   cancelar/reabrir. Alterne a aba/aplicativo e confirme que a câmera desliga.
   Confira que descrições e arquivo previamente escolhido permanecem ao alternar.
6. Negue a permissão da câmera: confira a orientação na tela e use **Enviar
   arquivo**. Para tentar novamente, libere a câmera nas permissões do site e
   do Android, feche aplicativos que a estejam usando e recarregue a página.
   Repita em desktop com webcam (ou sem câmera, verificando a alternativa).

`pytest -q` cobre ponte de captura, validação, origem ativa, campos, salvamento
e Word. Com Node disponível, também executa `tests/rear_camera.test.cjs`
usando apenas o runner nativo do Node: APIs simuladas verificam constraints,
troca de câmera, cancelamento, tracks e falhas. Sem Node esse teste é marcado
como ignorado, mantendo os testes Python. Não substituem este roteiro em
hardware real nem validam a escolha física das lentes pelo navegador.

## Migração Excel -> SQLite

```bash
python scripts/migrate_excel_to_sqlite.py
```
