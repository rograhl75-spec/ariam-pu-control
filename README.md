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

## Evidências fotográficas: múltiplas fotos por inspeção

Nas inspeções, escolha **Origem da evidência fotográfica**:
**Enviar arquivo** (JPG/JPEG/PNG/WebP, com seleção múltipla) ou
**Tirar foto com câmera traseira**. É possível misturar as duas origens
na mesma inspeção:

1. Capture uma foto ou selecione um ou vários arquivos.
2. Toque em **Adicionar evidências à inspeção** para manter as imagens na sessão.
3. Confira as miniaturas na galeria. Use **Remover foto N** para excluir
   individualmente ou **Limpar evidências** para esvaziar a coleção e as entradas.
4. Capture e adicione outras fotos, ou alterne para upload. As fotos **já
   adicionadas** não são substituídas nem descartadas ao trocar de origem,
   cancelar a câmera ou repetir a captura.
5. Somente depois de revisar todas as evidências, salve a inspeção/ gere o laudo.

Uma captura ainda **pendente**, não adicionada, é substituída pela próxima
tentativa e descartada ao sair da origem câmera. Adicione-a antes de continuar.
Arquivos pendentes permanecem selecionados ao alternar a origem, mas somente
a seleção ativa é adicionada. Uma seleção ativa pendente impede o salvamento
até ser adicionada ou descartada, evitando omissões silenciosas.
Após salvar com sucesso, a coleção é limpa para não reutilizar fotos na próxima
inspeção. A coleção não salva vive apenas na sessão: salve antes de fechar ou
recarregar o navegador.

Na tela legada (`streamlit run app_tablet.py`), a seção
**4 Anexo de Evidência Fotográfica & Conclusão** mantém as descrições durante
as adições e remoções. Ao terminar, clique em
**Salvar Inspeção e Gerar Laudo Técnico**. Todas as imagens são salvas com nomes
únicos em `fotos_inspecoes/`, referenciadas na coluna JSON `Foto_Paths` de
`Log_Inspecoes_Semanais.xlsx` e incorporadas ao Word, na ordem da galeria.
`Foto_Path` continua contendo a primeira foto por compatibilidade; registros
antigos com apenas essa coluna continuam gerando laudo.
Após salvar, o histórico seleciona automaticamente o ID recém-gravado; o
download deve corresponder àquela inspeção e conter **todas as imagens
anexadas, na ordem da galeria**, inclusive anexos com nomes ou conteúdos iguais.
Cada imagem recebe a legenda **Evidência N de Total**. Para baixar outra
inspeção, altere o ID no histórico.
Se uma imagem estiver ausente ou inválida, o download do laudo legado será
bloqueado com a identificação das evidências indisponíveis, em vez de oferecer
um documento parcial. A lista salva não é alterada: restaure os arquivos
originais nos caminhos registrados e gere novamente.
Mantenha a pasta de fotos junto à planilha para regenerar laudos posteriormente.
No app modular (`app.py`), **Salvar inspeção** grava os nomes e os caminhos
no SQLite, os bytes em `fotos_inspecoes/` junto ao banco, e disponibiliza
**Baixar laudo da última inspeção**, com todas as imagens.

**Diagnóstico e cobertura da correção:** a PR #7 tratava a seleção da inspeção,
mas essa alteração ainda não estava no código-base desta sessão: o salvamento
atualizava `ultimo_insp_id`, não o seletor `select_id_insp_banco`. Assim, após
salvar, o download podia continuar apontando para uma inspeção anterior com
uma única foto. O renderizador já percorria `Foto_Paths`, mas também permitia
baixar laudos parciais quando algum arquivo falhava. A correção atualiza o
seletor e impede essa exportação incompleta. Os testes exercitam câmera e
upload nos dois aplicativos, releitura de Excel/SQLite, conteúdo e ordem das
imagens no DOCX, anexos repetidos sem sobrescrita, inspeções consecutivas,
navegação pelo histórico, `Foto_Path` legado e recuperação de arquivos ausentes
ou inválidos. Não foi identificado truncamento das listas na persistência.

**Limitações:** fotos cujo arquivo já foi perdido não podem ser reconstruídas
pela lista de caminhos; precisam ser restauradas de uma cópia de segurança.
O laudo é exportado em Word (.docx), não em PDF. Os testes de câmera usam
simulação; a câmera física e a exibição do documento no Word do tablet/desktop
devem ser conferidas no roteiro manual abaixo.

O limite é de **20 fotos por inspeção** e **5 MiB por imagem**, tanto no arquivo
de entrada quanto no PNG normalizado. Câmera e upload passam pela mesma
validação, correção de orientação e conversão. Se um lote contiver uma imagem
inválida ou exceder a quantidade, nenhuma imagem desse lote será adicionada;
as evidências anteriores permanecem intactas. Remova fotos ou reduza o lote
antes de adicionar novas. Ao atingir 20 fotos, a câmera fica desativada até
remover uma evidência.

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
2. Capture e clique em **Adicionar evidências à inspeção**. Repita com pelo
   menos três fotos. Confira todas as miniaturas e as descrições preenchidas.
3. Troque para **Enviar arquivo**, selecione dois arquivos diferentes e
   adicione-os. Remova uma foto individual e confira que as demais permanecem.
   Volte à câmera e adicione outra foto; teste cancelar/reabrir sem perder a galeria.
4. Salve a inspeção, selecione seu ID no histórico e baixe o laudo Word.
   Confira a quantidade, ordem e orientação de todas as imagens. No modular,
   use **Baixar laudo da última inspeção**. Confirme que a próxima inspeção
   começa sem as fotos já salvas.
5. Em uma nova inspeção, teste **Limpar evidências**, re-renderizações e o limite
   de 20 fotos. Remova uma foto para liberar a câmera. Teste arquivo acima de
   5 MiB e lote inválido. Alterne a aba/aplicativo e confirme que a câmera desliga.
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
