# Caixa do grupo

Aplicativo Streamlit para cadastrar pessoas e produtos, registrar vendas de uma unidade com desconto opcional e conferir o extrato compartilhado por Pix, crédito e débito.

## Uso
1. Informe a senha do grupo.
2. Crie seu cadastro pelo nome e selecione-o no menu.
3. Em Produtos, cadastre nome, ícone e preço.
4. Em Vender, escolha o produto, confira o preço, selecione o pagamento e confirme.
5. Em Vendas do dia, acompanhe todos os integrantes, filtre datas/pessoa/pagamento e baixe o CSV. Para corrigir uma venda, cancele com motivo e registre outra.

Uma senha compartilhada dá os mesmos poderes a todos: selecionar um nome não comprova identidade individual. O sistema registra o pagamento informado; não processa cobranças nem verifica recebimento bancário.

## Armazenamento temporário
O arquivo SQLite fica dentro da aplicação e é compartilhado pelas sessões do mesmo servidor. A hospedagem pode apagar esse arquivo ao reiniciar, atualizar ou substituir o servidor, inclusive no mesmo dia. **Baixe o extrato para guardar os registros.** Não há garantia de backup ou permanência. A mudança de dia não apaga vendas automaticamente.

O CSV inclui a situação de cada venda. Linhas canceladas são históricas e não entram nos totais do aplicativo. Textos que poderiam ser interpretados como fórmula recebem o prefixo `texto: ` na exportação, preservando o original no cadastro.

## Executar
Python 3.12 ou mais recente.

```sh
python -m venv .venv
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Use o Python do ambiente criado. Configure uma senha própria de 12 a 128 caracteres em `GROUP_PASSWORD`, no gerenciador Secrets do Streamlit. Localmente, a mesma chave pode ser definida em `.streamlit/secrets.toml`, arquivo ignorado pelo Git. Não há senha padrão. Sem configuração, o aplicativo permanece fechado e não carrega vendas.

## Publicar no Streamlit
Selecione o repositório, a branch `main` e `app.py`; configure `GROUP_PASSWORD` em Advanced settings/Secrets. Não envie o banco, pastas de testes locais ou arquivos de segredos ao GitHub. O responsável pela hospedagem configura e distribui a senha ao grupo.

## Testes
```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Usam somente dados fictícios e pastas temporárias. `CAIXA_DATA_DIR` permite direcionar o arquivo de dados a uma pasta isolada em testes locais; não é uma entrada da interface pública.
