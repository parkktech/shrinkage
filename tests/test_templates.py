"""Template support: twig symbols, phtml/blade/ref-only reference counting."""
from conftest import run
from parsers import parse_text


def test_twig_blocks_and_macros():
    src = ("{% extends 'base.html.twig' %}\n"
           "{% block content %}\n{% endblock %}\n"
           "{% macro price(amount, currency = 'USD') %}\n{% endmacro %}\n")
    got = {(s.kind, s.name) for s in parse_text("page.html.twig", src)}
    assert ("f", "content") in got and ("f", "price") in got


def test_phtml_references_keep_symbols_alive(repo):
    (repo / "ViewModel.php").write_text(
        "<?php\nclass ViewModel\n{\n"
        "    public function getPromoLabel(): string\n    {\n        return 'x';\n    }\n}\n")
    (repo / "banner.phtml").write_text(
        "<div><?= $viewModel->getPromoLabel() ?></div>\n")
    run("codemap.py", "build", cwd=repo)
    map_text = (repo / ".claude" / "codemap.txt").read_text()
    line = next(l for l in map_text.splitlines() if "getPromoLabel" in l)
    assert "x1" in line, f"template usage must count as a reference: {line}"


def test_ref_only_config_counts(repo):
    (repo / "Observer.php").write_text(
        "<?php\nclass CheckoutObserver\n{\n"
        "    public function execute(): void\n    {\n    }\n}\n")
    (repo / "events.xml").write_text(
        '<config><event name="checkout_submit">'
        '<observer name="x" instance="CheckoutObserver"/></event></config>\n')
    run("codemap.py", "build", cwd=repo)
    map_text = (repo / ".claude" / "codemap.txt").read_text()
    line = next(l for l in map_text.splitlines() if "c CheckoutObserver" in l)
    assert "x1" in line, f"XML config reference must count: {line}"


def test_blade_and_vue_indexed(repo):
    (repo / "widget.blade.php").write_text(
        "@if($order->isPaid())\n<span>{{ $order->total() }}</span>\n@endif\n")
    (repo / "Cart.vue").write_text(
        "<template><div>{{ total }}</div></template>\n<script>\n"
        "export function computeTotal(items) {\n  return items.length;\n}\n</script>\n")
    run("codemap.py", "build", cwd=repo)
    map_text = (repo / ".claude" / "codemap.txt").read_text()
    assert "Cart.vue" in map_text and "computeTotal" in map_text
