# Plano do caixa compartilhado


## Decisões atuais
O usuário confirmou cadastro simples por nome, produtos com ícone/preço, uma unidade por venda, desconto opcional, pagamento Pix/crédito/débito, página Vendas do dia para todos e senha única do grupo. Autorizou usar GitHub e Streamlit abertos para publicar. Depois simplificou expressamente: dados dentro do próprio app para uso no dia, sem banco externo. Esta versão substitui a proposta de PostgreSQL.

## Primeira entrega
Três páginas: Vender, Produtos e Vendas do dia. Pessoa ativa visível; criação de pessoa pelo nome; cartão de produto com ícone, nome, preço e botão Vender. A confirmação mostra uma unidade, permite alterar preço e exige pagamento. Sucesso apenas após gravar.

Vendas do dia começa em hoje no horário de Brasília e mostra todos os integrantes. Total vendido, unidades, valores por pagamento, pessoa e produto. Filtros por período, pessoa e pagamento; extrato detalhado e download CSV. Atualizar ao abrir, mudar filtro, registrar ou cancelar, ou tocar Atualizar. Sem promessa de atualização contínua.

Tema claro, controles legíveis e confortáveis no celular. Sem gráficos decorativos, estoque, compradores, CPF, taxas, lucro, cobrança, parcelas, pagamento dividido ou modo offline.

## Regras
- Nome é atribuição, não autenticação individual. Quem possui a senha pode usar qualquer nome.
- Valores em centavos inteiros; decimal exato de até duas casas, positivo e até R$ 999.999,99. Desconto só naquela venda; sem gratuidade ou acréscimo.
- Guardar nomes e preço do momento da venda. Chave única por proposta: repetição recupera o registro, inclusive cancelado, sem duplicar nem reativar.
- Corrigir venda por cancelamento com motivo e novo lançamento; não editar venda confirmada. Cancelados continuam no histórico e saem dos totais ativos.
- Produto alterado durante uma proposta invalida proposta ainda não gravada. Recuperação de confirmação já persistida vem antes dessa validação.
- Renomear/arquivar produto não muda histórico; agrupamento por ID usa nome mais recente do recorte, e cada linha mantém seu nome histórico. Arquivados continuam na consulta.
- Guardar UTC; consultar dia de Brasília por intervalo fechado no início e aberto no fim. Totais e extrato compartilham filtros e o mesmo conjunto de vendas ativas.
- Crédito é venda declarada, não saldo recebido. Erro ao consultar não é faturamento zero.

## Armazenamento temporário
SQLite da biblioteca padrão em `data/caixa.sqlite3`, compartilhado por sessões do mesmo servidor. Conexões curtas, transações `BEGIN IMMEDIATE`, timeout e chave única. Não apagar na virada do dia. Streamlit pode apagar arquivos durante reinício/atualização/substituição do servidor, inclusive no mesmo dia. Aviso visível e download do extrato; não prometer permanência. Não há Supabase, conta adicional nem serviço pago.

## Acesso
Senha somente em Streamlit Secrets (`GROUP_PASSWORD`), entre 12 e 128 caracteres, comparação em tempo constante. Sem senha padrão; configuração ausente fecha o app. Nunca imprimir o segredo ou gravá-lo no Git.

Sessão máxima de oito horas e trinta minutos de inatividade, conferidas antes de dados/operações; fingerprint da configuração invalida sessão após troca de senha. Limite global atômico de vinte verificações por janela móvel de sessenta segundos no SQLite. Tentativas recusadas não ampliam a janela; erro no limitador impede login. Sob abuso o grupo pode ter atraso para novos logins; sessões já válidas não consomem essa cota. Perda do arquivo também reinicia o contador, limitação do armazenamento temporário.

SQL parametrizado, textos escapados, ícones permitidos e limites de tamanho. CSV UTF-8 sem BOM, ponto e vírgula, decimal pt-BR; células textuais com prefixos de fórmula, inclusive após espaços/controles e normalização Unicode, recebem `texto: `; original mantido no banco. Exportações podem ser compartilhadas pelos integrantes; não prometem revogação depois do download.

## Etapas e conferência
1. Criar `caixa/domain.py`, `store.py`, `auth.py`, `reports.py`. Testar com `python -m pytest -q`, dados fictícios, diretórios temporários: dinheiro, desconto, erros, duplicatas, duas gravações concorrentes, cancelamento, meia-noite e CSV.
2. Criar `app.py` e tema Streamlit. Streamlit AppTest e fumaça no navegador em porta separada, desktop/celular, fluxo entrada > nome > produto > venda > página compartilhada > extrato > sair.
3. Criar README, MAPEAMENTO, dependências fixadas e gitignore; relacionar regras aos testes; excluir bancos, segredos e arquivos locais. Finalizar ficha do produto. Sugerir id `caixa-grupo` no mapa sem mudar configuração global.
4. Revisar por unidade antes de publicar, confirmar/derrubar candidatos independentemente. Rodar suíte completa. Somente dados fictícios.
5. Publicar fonte limpa no GitHub e Streamlit, autorizado pelo usuário. Usuário define senha em Secrets; até isso, app fica fechado. Conferir URL e fluxo com dados fictícios.


Fonte: https://docs.streamlit.io/develop/concepts/connections/connecting-to-data
