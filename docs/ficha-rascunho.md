# Caixa do grupo

- id proposto: `caixa-grupo`.
- Tipo: ferramenta interna de um grupo; fase: construção.
- Pasta proposta: `C:\Users\Leonardo Pessoa\Documents\2. PROJETOS\Design\caixa-grupo`.
- Projeto de memória atual: `design`; este aplicativo ainda não tem entrada própria no mapa.
- Ficha definitiva prevista, após aprovação: `C:\Users\Leonardo Pessoa\Documents\2. PROJETOS\Leo\cerebro\projetos\caixa-grupo\ficha.md`.
- Sugestão de cadastro posterior em `C:\Users\Leonardo Pessoa\Documents\2. PROJETOS\Memória\alinhamento\projetos.json`: id `caixa-grupo`, apontando para a pasta proposta. Nenhuma configuração global foi alterada.

## Em uma frase
Aplicativo online no Streamlit para os integrantes de um grupo identificarem suas vendas por nome, cadastrarem produtos e consultarem o faturamento registrado de todos.

## Confirmado pelo usuário
- Cadastro simples de uma pessoa pelo nome.
- Produtos com nome, ícone e preço padrão.
- Uma unidade vendida a cada registro, com possibilidade de desconto nessa venda.
- Escolha obrigatória entre Pix, cartão de crédito e cartão de débito.
- Extrato com produtos, quantidades e valores por forma de pagamento.
- Todos podem ver o que os demais vendem; página compartilhada Vendas do dia.
- Uma senha única do grupo para acessar o aplicativo.
- Hospedagem desejada: Streamlit online.

## Propostas que ainda dependem do plano aprovado
- Uso no celular e computador, com internet, por um grupo de confiança.
- Seleção de nome representa atribuição da venda, sem identidade individual comprovada; quem tem a senha do grupo pode selecionar qualquer nome.
- Nomes e produtos com mesmo nome dentro da mesma pessoa não são duplicados; produtos iguais de pessoas diferentes são independentes.
- Quem tem a senha pode cadastrar pessoas/produtos, registrar vendas e cancelar lançamentos. Não haverá permissões individuais; essa consequência precisa ser aceita no plano.
- Cancelamento pede confirmação e motivo, preserva a venda e não a conta nos totais ativos; não há exclusão definitiva de vendas na interface.
- Consulta por dia no horário de Brasília, filtro por pessoa/produto/pagamento e extrato por intervalo de datas.
- Exportação CSV dos lançamentos filtrados. Não haverá fechamento que apague ou zere registros.
- Ícone escolhido em uma lista curta de emojis; upload de fotos fica de fora da primeira versão.
- Decisão posterior do usuário: SQLite dentro do app para uso temporário no dia, sem banco externo; perda possível após reinício/atualização, inclusive no mesmo dia. Download CSV disponível para guardar o extrato.

## Objetivo e limites
- Problema: reunir as vendas do grupo e conferir quantidades e valores sem somar cada meio de pagamento manualmente.
- Como o grupo controla hoje, tamanho exato, tipo de evento/negócio e custo atual: não informados; não inventar esses dados.
- Sucesso da primeira versão: uma venda confirmada aparece uma vez no extrato correto e a soma de seus registros corresponde aos totais exibidos, inclusive com desconto e cancelamento.
- Aplicativo registra o pagamento informado; não cobra, verifica Pix, lê máquina de cartão, calcula lucro, faz conciliação bancária ou desconta taxas.
- Fora de escopo: estoque, clientes/compradores, dados de cartão, CPF, múltiplos grupos, múltiplos perfis de permissão, parcelas, pagamentos divididos, modo offline e emissão fiscal.
- Sem integrações de pagamento; somente hospedagem e banco externo. Não usa modelos de linguagem.
- Dados: nomes/apelidos de vendedores, produtos e registros financeiros. Testes apenas com dados fictícios e banco separado.
- Pagamento pelo aplicativo, orçamento e prazo comercial: não informados; nenhum serviço pago será contratado neste planejamento.

## Fluxos principais
1. Integrante informa senha do grupo, cria ou seleciona seu nome e acessa os produtos.
2. Integrante cadastra produto, ícone e preço; o cartão passa a aparecer em Vender.
3. Integrante toca Vender, confere o preço, aplica desconto opcional, escolhe pagamento e confirma; o aplicativo confirma somente depois da gravação.
4. Qualquer integrante consulta Vendas do dia, vê os totais do grupo e os registros de cada pessoa.
5. Integrante escolhe período, consulta extrato, exporta e, se necessário, cancela um lançamento com motivo.

## Critérios de aceitação
- R-01: senha incorreta não libera páginas, relatórios ou gravações.
- R-02: pessoa e produto cadastrados ficam disponíveis entre sessões e recarregamentos enquanto existir o arquivo local; a hospedagem não garante permanência do arquivo.
- R-03: uma confirmação gera uma venda de uma unidade, com pessoa, produto, valor final, pagamento, horário e identificador.
- R-04: desconto não muda preço padrão nem vendas antigas; produto renomeado também não muda extratos anteriores.
- R-05: pagamento ausente/inválido, valor inválido e produto inexistente são recusados.
- R-06: duas pessoas podem registrar vendas ao mesmo tempo sem sobrescrever a venda da outra; repetição da mesma confirmação não duplica lançamento.
- R-07: Vendas do dia mostra todas as pessoas por padrão e aplica filtros sem misturar dia de Brasília com UTC.
- R-08: os totais por pessoa, produto e pagamento correspondem aos mesmos lançamentos válidos do extrato.
- R-09: cancelamento mantém histórico e motivo, exclui venda dos totais ativos e pode ser consultado.
- R-10: exportação preserva o recorte mostrado, formatos compreensíveis e neutraliza células que poderiam virar fórmulas em planilhas.
- R-11: indisponibilidade do banco não aparece como faturamento zero nem como venda confirmada.
- R-12: layout permite concluir cadastro, venda e consulta no celular e computador; operação de venda não depende só do ícone ou de cor.

## Triagem de design

## Próxima entrega
Construção da versão simples, testes fictícios e publicação autorizada em GitHub/Streamlit. Senha será configurada pelo usuário no painel do Streamlit.
