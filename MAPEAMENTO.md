# Mapeamento do caixa do grupo

Aplicativo Streamlit para vendas de um único grupo: cadastro por nome, produtos com ícone/preço, desconto por venda, Pix/crédito/débito e extrato compartilhado. SQLite temporário dentro do app, sem promessa de persistência na hospedagem. Senha única, sem identidade/permissão individual.

Ficha: `C:\Users\Leonardo Pessoa\Documents\2. PROJETOS\Leo\cerebro\projetos\caixa-grupo\ficha.md`.
Plano atual: [caixa compartilhado](docs/designs/2026-11-26-caixa-compartilhado.md).

## Regras do produto
- R-01 · Sem senha ou sessão válida não carregar dados nem operar — `tests/test_app.py`: `test_app_closed_without_secret`, `test_login_wrong_and_logout`; `tests/test_core.py`: `test_auth_expiry_rotation_and_global_limit`, `test_parallel_login_limit`, `test_invalid_secret_or_session`.
- R-02 · Cadastro compartilhado enquanto existir o arquivo local; duplicatas recusadas — `test_people_products_and_reopen`, `test_bad_person`.
- R-03 · Uma confirmação registra uma unidade com pessoa, produto, valor, pagamento e horário — `test_sale_discount_and_idempotency`, `test_end_to_end_synthetic`.
- R-04 · Desconto e mudança no catálogo não alteram histórico; proposta desatualizada é recusada — `test_stale_proposal_historical_snapshot_and_replay`, `test_archived_product_not_sold_but_keeps_history`.
- R-05 · Valores/pagamentos inválidos recusados — `test_money_rejects_invalid`, `test_bad_sale`, `test_end_to_end_synthetic`.
- R-06 · Gravações simultâneas não se perdem e reenvio não duplica — `test_parallel_distinct_and_repeated_confirmations`, `test_sale_discount_and_idempotency`.
- R-07 · Dia de Brasília e filtros selecionados — `test_midnight_brasilia`, `test_method_scenario_filters_and_csv`.
- R-08 · Totais por produto/pessoa/pagamento usam vendas ativas do mesmo conjunto — `test_method_scenario_filters_and_csv`, `test_product_groups_keep_person_separate`.
- R-09 · Cancelar preserva histórico e repetição não reativa venda — `test_cancel_and_replay_do_not_resurrect`, `test_cancel_invalid`, `test_end_to_end_synthetic`.
- R-10 · CSV conserva dados e situação; neutraliza fórmulas — `test_csv_formula_text`, `test_csv_quotes_accents_and_formula`, `test_method_scenario_filters_and_csv`.
- R-11 · Falha de acesso não se apresenta como zero/sucesso — tratamento em `app.py`; teste de falha de gravação/consulta será acrescentado antes da publicação.
- R-12 · Caminho de cadastro/venda/consulta utilizável — `test_end_to_end_synthetic`; fumaça visual desktop/celular pendente.

## M-001 · Cancelamento selecionava outra venda
- Tipo: funcional
- Data e versão: 26/11/2026 · primeira versão em desenvolvimento
- O que a aplicação deve fazer: cancelar somente a venda escolhida e confirmada pelo integrante.
- O que aconteceu: se outra sessão cancelasse essa venda enquanto o formulário estava aberto, a lista era reconstruída e o formulário podia escolher automaticamente outra venda.
- Causa: seletor só com vendas ativas e seleção inicial automática.
- Correção: manter a seleção explícita por identificador estável, incluir canceladas no recorte e recusar envio sem alvo selecionado.
- Teste de regressão: `tests/test_app.py` › "M-001: cancelamento em outra sessão não troca a venda selecionada".
