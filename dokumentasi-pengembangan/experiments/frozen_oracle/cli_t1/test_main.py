import pytest
import main

def _get_matrix(data):
    if hasattr(main, 'Matrix'):
        return main.Matrix(data)
    return data

def _to_list(mat):
    if hasattr(mat, 'data'):
        return mat.data
    return mat

def _add(a, b):
    m1 = _get_matrix(a)
    m2 = _get_matrix(b)
    if hasattr(m1, '__add__') and not isinstance(m1, list):
        return _to_list(m1 + m2)
    elif hasattr(main, 'add_matrices'):
        return _to_list(main.add_matrices(a, b))
    raise AttributeError("Tidak ditemukan metode penjumlahan matriks")

def _sub(a, b):
    m1 = _get_matrix(a)
    m2 = _get_matrix(b)
    if hasattr(m1, '__sub__') and not isinstance(m1, list):
        return _to_list(m1 - m2)
    elif hasattr(main, 'subtract_matrices'):
        return _to_list(main.subtract_matrices(a, b))
    raise AttributeError("Tidak ditemukan metode pengurangan matriks")

def _mul(a, b):
    m1 = _get_matrix(a)
    m2 = _get_matrix(b)
    if hasattr(m1, '__mul__') and not isinstance(m1, list):
        return _to_list(m1 * m2)
    elif hasattr(main, 'multiply_matrices'):
        return _to_list(main.multiply_matrices(a, b))
    raise AttributeError("Tidak ditemukan metode perkalian matriks")

def test_matrix_addition():
    """Menguji penjumlahan dua matriks 2x2 secara matematis."""
    a = [[1, 2], [3, 4]]
    b = [[5, 6], [7, 8]]
    res = _add(a, b)
    assert res in ([[6, 8], [10, 12]], [[6.0, 8.0], [10.0, 12.0]])

def test_matrix_subtraction():
    """Menguji pengurangan dua matriks 2x2 secara matematis."""
    a = [[5, 6], [7, 8]]
    b = [[1, 2], [3, 4]]
    res = _sub(a, b)
    assert res in ([[4, 4], [4, 4]], [[4.0, 4.0], [4.0, 4.0]])

def test_matrix_multiplication():
    """Menguji perkalian dot product dua matriks 2x2 secara matematis."""
    a = [[1, 2], [3, 4]]
    b = [[5, 6], [7, 8]]
    res = _mul(a, b)
    assert res in ([[19, 22], [43, 50]], [[19.0, 22.0], [43.0, 50.0]])

def test_matrix_addition_incompatible_dimensions():
    """Menguji bahwa penjumlahan matriks beda dimensi (2x2 vs 2x3) melempar ValueError."""
    a = [[1, 2], [3, 4]]
    b = [[1, 2, 3], [4, 5, 6]]
    with pytest.raises(ValueError):
        _add(a, b)

def test_matrix_multiplication_incompatible_dimensions():
    """Menguji bahwa perkalian matriks beda dimensi incompatible (2x3 vs 2x3) melempar ValueError."""
    a = [[1, 2, 3], [4, 5, 6]]
    b = [[1, 2, 3], [4, 5, 6]]
    with pytest.raises(ValueError):
        _mul(a, b)
