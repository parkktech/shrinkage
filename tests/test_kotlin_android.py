"""Kotlin parser + Android reference-only indexing and detection."""
from conftest import run
from parsers import parse_text


def test_kotlin_symbols():
    src = ("class OrderRepo(private val api: Api) : Repo, Cacheable {\n"
           "    suspend fun fetch(id: String, force: Boolean = false): Order {\n"
           "        return api.get(id)\n    }\n}\n"
           "interface Repo {\n    fun refresh()\n}\n"
           "object Formatter {\n    fun money(cents: Long): String = \"$cents\"\n}\n"
           "fun String.truncate(max: Int = 20): String = take(max)\n"
           "fun topLevel(x: Int) = x * 2\n")
    got = {(s.kind, s.parent, s.name) for s in parse_text("a.kt", src)}
    assert ("c", "", "OrderRepo") in got and ("m", "OrderRepo", "fetch") in got
    assert ("i", "", "Repo") in got and ("m", "Repo", "refresh") in got
    assert ("c", "", "Formatter") in got and ("m", "Formatter", "money") in got
    assert ("m", "String", "truncate") in got, "extension fun groups under receiver"
    assert ("f", "", "topLevel") in got


def test_manifest_and_layout_refs_keep_kotlin_alive(repo):
    (repo / "PayService.kt").write_text(
        "class PayService {\n    fun onHandle(): Int {\n        return 1\n    }\n}\n")
    (repo / "AndroidManifest.xml").write_text(
        '<manifest><application><service android:name=".PayService"/></application></manifest>\n')
    layout = repo / "res" / "layout"
    layout.mkdir(parents=True)
    (layout / "checkout.xml").write_text(
        '<Button android:onClick="onHandle"/>\n')
    run("codemap.py", "build", cwd=repo)
    m = (repo / ".claude" / "codemap.txt").read_text()
    cls = next(l for l in m.splitlines() if "c PayService" in l)
    fn = next(l for l in m.splitlines() if "onHandle(" in l)
    assert "x1" in cls and "x1" in fn, f"manifest/layout refs must count: {cls} / {fn}"


def test_android_detection(repo):
    (repo / "build.gradle.kts").write_text("plugins { id(\"com.android.application\") }\n")
    (repo / "Main.kt").write_text("fun main() {\n}\n")
    code, out = run("codemap.py", "build", cwd=repo)
    assert "android" in out and "frameworks/android.md" in out
