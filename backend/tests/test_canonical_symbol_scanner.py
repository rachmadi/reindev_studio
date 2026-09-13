"""
Tests for universal canonical_symbol_scanner across Python and Dart grammar constructs.
Verifies grammar-aware parsing of classes, constructors, methods, arrow functions,
getters/setters, and top-level variables. Zero task-specific symbols.
"""

import pytest
from backend.canonical_symbol_scanner import (
    CanonicalSymbolResolution,
    scan_symbols_from_code,
    scan_symbols_from_files,
    scan_code_symbols,
    has_symbol,
)


class TestPythonSymbolScanning:
    """Test Python AST symbol extraction."""

    def test_python_classes_and_methods(self):
        code = """
class Calculator:
    def __init__(self, precision: int = 2):
        self.precision = precision

    def add(self, a: float, b: float) -> float:
        return a + b

    async def fetch_rates(self) -> dict:
        return {"USD": 1.0}
"""
        res = scan_symbols_from_code(code, "python")
        assert "Calculator" in res.class_names
        assert "add" in res.functions
        assert "fetch_rates" in res.functions
        assert "__init__" in res.functions
        assert "add" in res.classes["Calculator"]["methods"]

    def test_python_top_level_variables_and_functions(self):
        code = """
API_VERSION = "v1"
DEBUG_MODE = True
app = create_app()

def run_server():
    pass
"""
        res = scan_symbols_from_code(code, "python")
        assert "API_VERSION" in res.top_level_declarations
        assert "DEBUG_MODE" in res.top_level_declarations
        assert "app" in res.top_level_declarations
        assert "run_server" in res.functions
        assert res.all_symbols.issuperset({"API_VERSION", "DEBUG_MODE", "app", "run_server"})


class TestDartSymbolScanning:
    """Test Dart grammar-aware symbol extraction."""

    def test_dart_classes_and_constructors(self):
        code = """
class MetricCard extends StatelessWidget {
  final String title;
  final double value;

  const MetricCard({
    Key? key,
    required this.title,
    required this.value,
  }) : super(key: key);

  MetricCard.compact(this.title) : value = 0.0;

  @override
  Widget build(BuildContext context) {
    return Container();
  }
}
"""
        res = scan_symbols_from_code(code, "dart")
        assert "MetricCard" in res.class_names
        assert "build" in res.functions
        assert "MetricCard" in res.classes

        # Constructor parameter extraction
        ctor_params = res.classes["MetricCard"].get("constructor_params", [])
        assert "title" in ctor_params
        assert "value" in ctor_params

    def test_dart_arrow_functions_and_getters_setters(self):
        code = """
class DataService {
  String _endpoint = "https://api.example.com";

  String get endpoint => _endpoint;
  set endpoint(String val) => _endpoint = val;

  int compute(int x) => x * 2;
  Future<void> syncData() async => await doSync();
}
"""
        res = scan_symbols_from_code(code, "dart")
        assert "DataService" in res.class_names
        assert "endpoint" in res.functions
        assert "compute" in res.functions
        assert "syncData" in res.functions

    def test_dart_top_level_variables_and_constants(self):
        code = """
const double defaultPadding = 16.0;
final metricProvider = StateNotifierProvider((ref) => Notifier());
var globalCounter = 0;
late final String appSecret;

void main() {
  runApp(const MyApp());
}
"""
        res = scan_symbols_from_code(code, "dart")
        assert "defaultPadding" in res.top_level_declarations
        assert "metricProvider" in res.top_level_declarations
        assert "globalCounter" in res.top_level_declarations
        assert "appSecret" in res.top_level_declarations
        assert "main" in res.functions

        # Check has_symbol lookup
        code_files = {"lib/main.dart": code}
        assert has_symbol(code_files, "metricProvider", "dart")
        assert has_symbol(code_files, "defaultPadding", "dart")
        assert has_symbol(code_files, "main", "dart")


class TestSymbolResolutionAdapters:
    """Test compatibility adapters for Phase Validators and Locked Invariants."""

    def test_scan_code_symbols_legacy_dict_python(self):
        code_files = {
            "main.py": """
class UserService:
    def get_user(self, user_id: str):
        pass
"""
        }
        result = scan_code_symbols(code_files, "python")
        assert isinstance(result, dict)
        assert "classes" in result
        assert "functions" in result
        assert "UserService" in result["classes"]
        assert "get_user" in result["functions"]

    def test_scan_code_symbols_legacy_dict_dart(self):
        code_files = {
            "lib/main.dart": """
class ItemCard {
  void render() {}
}
final itemProvider = Provider((ref) => ItemCard());
"""
        }
        result = scan_code_symbols(code_files, "dart")
        assert isinstance(result, dict)
        assert "ItemCard" in result["classes"]
        assert "render" in result["functions"]
        # Legacy adapter merges top_level_declarations into functions so `classes + functions` sees everything
        assert "itemProvider" in result["functions"]
        assert "itemProvider" in result["top_level_declarations"]
