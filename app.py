"""Interface do caixa compartilhado."""

import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import streamlit as st

from caixa.auth import authenticate, authorized, configured
from caixa.domain import ICONS, PAYMENTS, ZONE, Invalid, cents, day_bounds, decimal_text, local_time, money
from caixa.reports import export_csv, groups, totals
from caixa.store import Store

st.set_page_config(page_title="Caixa do grupo", page_icon=":material/point_of_sale:", layout="wide")


@st.cache_resource
def database(path):
    return Store(path)


def clear_session():
    for key in list(st.session_state):
        del st.session_state[key]


def login(store, secret):
    st.title("Caixa do grupo")
    st.write("Entre para registrar vendas e acompanhar o dia com o grupo.")
    with st.form("login"):
        password = st.text_input("Senha do grupo", type="password", max_chars=128, key="login_password")
        enter = st.form_submit_button("Entrar", type="primary", use_container_width=True)
    if enter:
        session, error = authenticate(password, secret, store)
        if session:
            clear_session()
            st.session_state["auth"] = session
            st.rerun()
        st.error(error)


def choose_person(store):
    people = store.people()
    names = {p["id"]: p["name"] for p in people}
    ids = list(names)
    with st.sidebar:
        st.header("Seu caixa")
        if st.session_state.get("person") not in ids:
            st.session_state.pop("person", None)
        person = st.selectbox("Quem está vendendo?", ids, index=None, format_func=names.get, placeholder="Selecione seu nome", key="person")
        with st.expander("Criar pessoa", expanded=not people):
            with st.form("create_person", clear_on_submit=True):
                name = st.text_input("Nome ou apelido", max_chars=60)
                if st.form_submit_button("Criar cadastro", use_container_width=True):
                    store.add_person(name)
                    st.session_state["notice"] = "Cadastro criado. Selecione seu nome na lista."
                    st.rerun()
        st.caption("Todos do grupo podem consultar e usar os cadastros.")
        if st.button("Sair", icon=":material/logout:", use_container_width=True):
            clear_session()
            st.rerun()
    return person, names


def show_sale(store, proposal):
    with st.container(border=True):
        st.subheader("Confirmar venda")
        st.text(f"{proposal['person_name']} · {proposal['name']} · 1 unidade")
        st.write(f"Preço cadastrado: {money(proposal['price'])}")
        suffix = proposal["operation"]
        change = st.toggle("Alterar preço desta venda", key="change_" + suffix)
        with st.form("sale_" + suffix):
            price = st.text_input("Valor da venda (R$)", value=decimal_text(proposal["price"]), disabled=not change, key="price_" + suffix)
            payment = st.radio("Como foi pago?", list(PAYMENTS), index=None, format_func=PAYMENTS.get, horizontal=True, key="payment_" + suffix)
            submit = st.form_submit_button("Confirmar venda", type="primary", use_container_width=True)
        if submit:
            sale = store.record(proposal, cents(price) if change else proposal["price"], payment)
            st.session_state.pop("proposal", None)
            st.session_state["notice"] = (
                "Essa confirmação já corresponde a uma venda cancelada. Confira o extrato."
                if sale["cancelled_at"] else f"Venda registrada: {money(sale['amount'])} em {PAYMENTS[sale['payment']]} .".replace(" .", ".")
            )
            st.rerun()
        if st.button("Voltar sem registrar", key="back_" + suffix):
            st.session_state.pop("proposal", None)
            st.rerun()


def sell_page(store, person, names):
    st.header("Vender")
    if not person:
        st.info("Crie ou selecione seu nome no menu para começar.")
        return
    st.text("Vendendo para o cadastro: " + names[person])
    proposal = st.session_state.get("proposal")
    if proposal and proposal["person_id"] != person:
        st.session_state.pop("proposal", None)
        proposal = None
    if proposal:
        show_sale(store, proposal)
        return
    products = store.products(person)
    if not products:
        st.info("Seu catálogo está vazio. Abra Produtos e adicione o primeiro item.")
        return
    for start in range(0, len(products), 3):
        columns = st.columns(3)
        for column, product in zip(columns, products[start:start + 3]):
            with column, st.container(border=True):
                st.text(product["name"])
                st.subheader(money(product["price"]))
                if st.button("Vender", icon=ICONS[product["icon"]], key="sell_" + product["id"], type="primary", use_container_width=True):
                    st.session_state["proposal"] = store.proposal(person, product["id"])
                    st.rerun()


def products_page(store, person, names):
    st.header("Produtos")
    if not person:
        st.info("Crie ou selecione seu nome no menu para cadastrar produtos.")
        return
    st.text("Produtos de " + names[person])
    with st.expander("Adicionar produto", expanded=True):
        with st.form("new_product", clear_on_submit=True):
            name = st.text_input("Nome do produto", max_chars=80)
            icon = st.selectbox("Ícone", list(ICONS))
            price = st.text_input("Preço padrão (R$)", placeholder="Ex.: 12,50")
            if st.form_submit_button("Cadastrar produto", type="primary"):
                store.save_product(person, name, icon, cents(price))
                st.session_state["notice"] = "Produto cadastrado. Ele já aparece em Vender."
                st.rerun()
    products = store.products(person, include_archived=True)
    for product in products:
        label = "Editar produto" if product["active"] else "Produto arquivado"
        st.text(product["name"] + " · " + money(product["price"]))
        with st.expander(label, icon=ICONS[product["icon"]]):
            with st.form("edit_" + product["id"]):
                name = st.text_input("Nome", value=product["name"], max_chars=80)
                icon = st.selectbox("Ícone", list(ICONS), index=list(ICONS).index(product["icon"]))
                price = st.text_input("Preço padrão (R$)", value=decimal_text(product["price"]))
                st.caption("Alterações valem para as próximas vendas. O histórico permanece igual.")
                if st.form_submit_button("Salvar produto"):
                    store.save_product(person, name, icon, cents(price), product["id"])
                    st.session_state["notice"] = "Produto atualizado."
                    st.rerun()
            action = "Arquivar produto" if product["active"] else "Reativar produto"
            if st.button(action, key="archive_" + product["id"]):
                store.archive_product(person, product["id"], not product["active"])
                st.rerun()


def daily_page(store, names):
    st.header("Vendas do dia")
    st.caption("Página compartilhada do grupo · Horários de Brasília")
    today = datetime.now(ZONE).date()
    with st.expander("Data e filtros", expanded=True):
        first = st.date_input("De", value=today, key="start_date")
        last = st.date_input("Até", value=today, key="end_date")
        person = st.selectbox("Pessoa", [None] + list(names), format_func=lambda p: "Todas as pessoas" if p is None else names[p])
        payment = st.selectbox("Pagamento", [None] + list(PAYMENTS), format_func=lambda p: "Todos os pagamentos" if p is None else PAYMENTS[p])
    start, end = day_bounds(first, last)
    if st.button("Atualizar", icon=":material/refresh:"):
        st.rerun()
    rows = store.sales(start, end, person, payment)
    summary = totals(rows)
    st.caption("Totais do período e filtros selecionados · consulta em " + datetime.now(ZONE).strftime("%H:%M:%S"))
    col1, col2 = st.columns(2)
    col1.metric("Valor vendido", money(summary["amount"]))
    col2.metric("Unidades vendidas", summary["units"])
    for key, label in PAYMENTS.items():
        st.write(f"{label}: {money(summary['payments'][key])}")
    st.caption("Valores informados nas vendas, antes de eventuais taxas. Cartão não significa saldo já recebido.")
    if not rows:
        st.info("Nenhuma venda neste período e nestes filtros.")
        return
    for field, title in (("person", "Por pessoa"), ("product", "Por produto")):
        st.subheader(title)
        records = []
        for item in groups(rows, field):
            record = {"Nome": item["name"], "Unidades": item["units"], "Vendido": money(item["amount"])}
            if field == "product":
                record["Pessoa"] = item["person"]
            records.append(record)
        if records:
            st.dataframe(records, hide_index=True, use_container_width=True)
    st.subheader("Extrato")
    show_cancelled = st.checkbox("Mostrar também vendas canceladas", value=True)
    visible = rows if show_cancelled else [r for r in rows if not r["cancelled_at"]]
    table = [{
        "Data e hora": local_time(r["created_at"]), "Pessoa": r["person_name"], "Produto": r["product_name"],
        "Valor": money(r["amount"]), "Desconto": money(r["base_price"] - r["amount"]),
        "Pagamento": PAYMENTS[r["payment"]], "Situação": "Cancelada" if r["cancelled_at"] else "Válida",
        "Motivo": r["cancel_reason"] or "",
    } for r in visible]
    st.dataframe(table, hide_index=True, use_container_width=True)
    st.caption("Vendas canceladas aparecem no histórico, mas não entram nos totais acima.")
    if "export_id" not in st.session_state:
        st.session_state["export_id"] = uuid4().hex
    st.download_button("Baixar extrato CSV", export_csv(visible), file_name=f"extrato-{first}-{last}-{st.session_state['export_id']}.csv", mime="text/csv", icon=":material/download:", on_click="ignore")
    candidates = {r["id"]: r for r in rows}
    if any(not r["cancelled_at"] for r in rows):
        with st.expander("Corrigir um lançamento"):
            st.write("Cancele a venda com o erro e registre uma nova em Vender. A original permanece no histórico.")
            with st.form("cancel_sale"):
                sale_id = st.selectbox("Venda a cancelar", list(candidates), index=None, key="sale_to_cancel", format_func=lambda sid: f"{local_time(candidates[sid]['created_at'])} · {candidates[sid]['person_name']} · {candidates[sid]['product_name']} · {money(candidates[sid]['amount'])} · {sid[:6]}" + (" · já cancelada" if candidates[sid]["cancelled_at"] else ""))
                reason = st.text_input("Motivo do cancelamento", max_chars=300)
                confirm = st.checkbox("Confirmo o cancelamento desta venda")
                if st.form_submit_button("Cancelar venda"):
                    if not sale_id or sale_id not in candidates:
                        raise Invalid("Selecione novamente a venda a cancelar.")
                    if not confirm:
                        raise Invalid("Marque a confirmação antes de cancelar.")
                    store.cancel(sale_id, reason)
                    st.session_state["notice"] = "Venda cancelada e preservada no histórico."
                    st.rerun()


def main():
    try:
        secret = st.secrets.get("GROUP_PASSWORD", "")
    except (FileNotFoundError, KeyError):
        secret = ""
    if not configured(secret):
        st.title("Caixa do grupo")
        st.info("Este caixa aguarda a configuração da senha pelo responsável.")
        st.caption("No painel do Streamlit, configure GROUP_PASSWORD em Secrets com 12 a 128 caracteres.")
        return
    data_dir = Path(os.environ.get("CAIXA_DATA_DIR", str(Path(__file__).parent / "data")))
    store = database(str(data_dir / "caixa.sqlite3"))
    session = st.session_state.get("auth")
    if not authorized(session, secret):
        if session:
            clear_session()
        login(store, secret)
        return
    session["last"] = time.time()
    person, names = choose_person(store)
    st.title("Caixa do grupo")
    st.caption("Dados temporários: um reinício ou atualização do servidor pode apagar os registros, inclusive no mesmo dia. Baixe o extrato para guardar suas vendas.")
    if notice := st.session_state.pop("notice", None):
        st.success(notice)
    page = st.radio("Navegação", ["Vender", "Produtos", "Vendas do dia"], horizontal=True, label_visibility="collapsed")
    if page == "Vender":
        sell_page(store, person, names)
    elif page == "Produtos":
        products_page(store, person, names)
    else:
        daily_page(store, names)


try:
    main()
except Invalid as exc:
    st.error(str(exc))
except (sqlite3.Error, OSError):
    st.error("Não foi possível acessar os registros. Tente novamente e confira o extrato antes de repetir uma venda.")
