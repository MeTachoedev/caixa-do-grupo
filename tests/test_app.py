from pathlib import Path

from streamlit.testing.v1 import AppTest
from caixa.store import Store

ROOT = Path(__file__).resolve().parents[1]
SECRET = "senha-ficticia-para-teste"


def app(monkeypatch, tmp_path, with_secret=True):
    monkeypatch.setenv("CAIXA_DATA_DIR", str(tmp_path))
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=15)
    if with_secret:
        at.secrets["GROUP_PASSWORD"] = SECRET
    else:
        at.secrets["GROUP_PASSWORD"] = ""
    return at.run()


def by_label(elements, label):
    return next(e for e in elements if e.label == label)


def enter(at):
    by_label(at.text_input, "Senha do grupo").set_value(SECRET)
    by_label(at.button, "Entrar").click().run()
    assert not at.exception
    return at


def test_app_closed_without_secret(monkeypatch, tmp_path):
    at = app(monkeypatch, tmp_path, False)
    assert not at.exception
    assert "aguarda" in at.info[0].value
    assert not at.radio
    assert not (tmp_path / "caixa.sqlite3").exists()


def test_login_wrong_and_logout(monkeypatch, tmp_path):
    at = app(monkeypatch, tmp_path)
    by_label(at.text_input, "Senha do grupo").set_value("incorreta")
    by_label(at.button, "Entrar").click().run()
    assert at.error[0].value == "Senha incorreta."
    assert not at.radio
    enter(at)
    by_label(at.button, "Sair").click().run()
    assert not at.exception
    assert not at.radio
    assert by_label(at.text_input, "Senha do grupo")


def test_end_to_end_synthetic(monkeypatch, tmp_path):
    at = enter(app(monkeypatch, tmp_path))
    by_label(at.text_input, "Nome ou apelido").set_value("Vendedor fictício")
    by_label(at.button, "Criar cadastro").click().run()
    selector = by_label(at.selectbox, "Quem está vendendo?")
    assert "Vendedor fictício" in selector.options
    person_id = Store(tmp_path / "caixa.sqlite3").people()[0]["id"]
    selector.set_value(person_id).run()
    assert not at.exception
    assert at.session_state["person"] == person_id
    by_label(at.radio, "Navegação").set_value("Produtos").run()
    by_label(at.text_input, "Nome do produto").set_value("Doce fictício")
    by_label(at.text_input, "Preço padrão (R$)").set_value("10,00")
    by_label(at.button, "Cadastrar produto").click().run()
    assert not at.exception
    by_label(at.radio, "Navegação").set_value("Vender").run()
    by_label(at.button, "Vender").click().run()
    by_label(at.button, "Confirmar venda").click().run()
    assert "Escolha" in at.error[0].value
    by_label(at.toggle, "Alterar preço desta venda").set_value(True).run()
    by_label(at.text_input, "Valor da venda (R$)").set_value("8,00")
    by_label(at.radio, "Como foi pago?").set_value("pix")
    by_label(at.button, "Confirmar venda").click().run()
    assert not at.exception
    assert "R$ 8,00" in at.success[0].value
    by_label(at.radio, "Navegação").set_value("Vendas do dia").run()
    assert not at.exception
    assert at.metric[0].value == "R$ 8,00"
    assert at.metric[1].value == "1"
    by_label(at.text_input, "Motivo do cancelamento").set_value("Exemplo de correção")
    by_label(at.selectbox, "Venda a cancelar").select_index(0)
    by_label(at.checkbox, "Confirmo o cancelamento desta venda").set_value(True)
    by_label(at.button, "Cancelar venda").click().run()
    assert not at.exception
    assert at.metric[0].value == "R$ 0,00"
    assert "Cancelada" in str(at.dataframe[-1].value)


def test_m001_concurrent_cancel_keeps_other_sale(monkeypatch, tmp_path):
    """M-001: cancelamento em outra sessão não troca a venda selecionada."""
    store = Store(tmp_path / "caixa.sqlite3")
    person = store.add_person("Pessoa fictícia concorrente")
    product = store.save_product(person, "Produto fictício", "Produto", 1000)
    first = store.record(store.proposal(person, product), 1000, "pix")
    second = store.record(store.proposal(person, product), 1000, "debito")
    at = enter(app(monkeypatch, tmp_path))
    by_label(at.radio, "Navegação").set_value("Vendas do dia").run()
    by_label(at.selectbox, "Venda a cancelar").set_value(first["id"])
    by_label(at.text_input, "Motivo do cancelamento").set_value("Correção fictícia na sessão A")
    by_label(at.checkbox, "Confirmo o cancelamento desta venda").set_value(True)
    store.cancel(first["id"], "Correção fictícia na sessão B")
    by_label(at.button, "Cancelar venda").click().run()
    assert not at.exception
    from datetime import date
    from caixa.domain import day_bounds
    rows = store.sales(*day_bounds(date(2000, 1, 1), date(2099, 1, 1)))
    assert next(r for r in rows if r["id"] == second["id"])["cancelled_at"] is None
    assert next(r for r in rows if r["id"] == first["id"])["cancel_reason"] == "Correção fictícia na sessão B"


def test_unavailable_sales_is_not_zero(monkeypatch, tmp_path):
    at = enter(app(monkeypatch, tmp_path))
    def unavailable(*_args, **_kwargs):
        import sqlite3
        raise sqlite3.OperationalError("falha fictícia")
    monkeypatch.setattr(Store, "sales", unavailable)
    by_label(at.radio, "Navegação").set_value("Vendas do dia").run()
    assert not at.exception
    assert "Não foi possível acessar" in at.error[0].value
    assert not at.metric
