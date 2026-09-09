"""
Unit tests untuk Architect Blueprint Validator (backend/architect_validator.py)
ReinDev Studio — Iterasi 6
"""

import pytest
from backend.architect_validator import (
    validate_python_blueprint_consistency,
    validate_dart_blueprint_consistency,
    validate_architect_blueprint
)

def test_python_blueprint_valid_imports():
    blueprint = '''
### Modul User
```python
from typing import Optional
from pydantic import BaseModel, Field, field_validator

class User(BaseModel):
    name: str = Field(...)
    
    @field_validator("name")
    def check_name(cls, v):
        return v.strip()
```
'''
    is_valid, errors = validate_python_blueprint_consistency(blueprint)
    assert is_valid
    assert len(errors) == 0


def test_python_blueprint_missing_decorator_import():
    blueprint = '''
### Modul User Cacat
```python
from typing import Optional
from pydantic import BaseModel, Field

class User(BaseModel):
    name: str = Field(...)
    
    @field_validator("name")
    def check_name(cls, v):
        return v.strip()
```
'''
    is_valid, errors = validate_python_blueprint_consistency(blueprint)
    assert not is_valid
    assert len(errors) == 1
    assert "@field_validator" in errors[0]
    assert "tidak ditemukan dalam statement import" in errors[0]


def test_python_blueprint_missing_base_class_import():
    blueprint = '''
### Modul Service Cacat
```python
class MyService(BaseService):
    def run(self):
        pass
```
'''
    is_valid, errors = validate_python_blueprint_consistency(blueprint)
    assert not is_valid
    assert any("BaseService" in err for err in errors)


def test_dart_blueprint_valid_constructor_and_invocation():
    blueprint = '''
### Widget Dart
```dart
class MetricCard {
  final String title;
  final double value;
  
  MetricCard({required this.title, required this.value});
}

Widget buildCard() {
  return MetricCard(title: "CPU", value: 45.0);
}
```
'''
    is_valid, errors = validate_dart_blueprint_consistency(blueprint)
    assert is_valid
    assert len(errors) == 0


def test_dart_blueprint_unknown_parameter_invocation():
    blueprint = '''
### Widget Dart Cacat
```dart
class MetricCard {
  final String title;
  final double value;
  
  MetricCard({required this.title, required this.value});
}

Widget buildCard() {
  return MetricCard(title: "CPU", value: 45.0, color: Colors.blue);
}
```
'''
    is_valid, errors = validate_dart_blueprint_consistency(blueprint)
    assert not is_valid
    assert any("color" in err and "MetricCard" in err for err in errors)


def test_dart_blueprint_abstract_class_instantiated():
    blueprint = '''
### Widget Dart Cacat Abstract
```dart
abstract class MetricData {
  String get title;
}

Widget buildCard() {
  final data = MetricData();
}
```
'''
    is_valid, errors = validate_dart_blueprint_consistency(blueprint)
    assert not is_valid
    assert any("abstract class" in err and "MetricData" in err for err in errors)


def test_universal_entry_point():
    py_bp = '```python\n@unknown_dec\ndef foo(): pass\n```'
    is_v_py, errs_py = validate_architect_blueprint(py_bp, "python")
    assert not is_v_py
    assert len(errs_py) > 0

    dart_bp = '```dart\nabstract class Foo {}\nvoid bar() { Foo(); }\n```'
    is_v_dart, errs_dart = validate_architect_blueprint(dart_bp, "dart")
    assert not is_v_dart
    assert len(errs_dart) > 0
