import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_create_product():
    """Menguji pembuatan produk baru dengan status 201 dan kembalian data lengkap."""
    payload = {"name": "Mechanical Keyboard", "quantity": 15}
    response = client.post("/products", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Mechanical Keyboard"
    assert data["quantity"] == 15
    assert "id" in data

def test_get_all_products():
    """Menguji pembacaan seluruh inventaris produk via GET /products."""
    response = client.get("/products")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1

def test_get_product_by_id():
    """Menguji pembacaan produk spesifik berdasarkan ID."""
    res = client.post("/products", json={"name": "Wireless Mouse", "quantity": 30})
    assert res.status_code == 201
    prod_id = res.json()["id"]
    
    res_get = client.get(f"/products/{prod_id}")
    assert res_get.status_code == 200
    assert res_get.json()["name"] == "Wireless Mouse"
    assert res_get.json()["quantity"] == 30

def test_delete_product():
    """Menguji penghapusan produk dengan status 204 dan verifikasi 404 setelahnya."""
    res = client.post("/products", json={"name": "USB-C Hub", "quantity": 5})
    assert res.status_code == 201
    prod_id = res.json()["id"]
    
    res_del = client.delete(f"/products/{prod_id}")
    assert res_del.status_code == 204
    
    res_check = client.get(f"/products/{prod_id}")
    assert res_check.status_code == 404

def test_delete_nonexistent_product():
    """Menguji respons 404 saat menghapus ID yang tidak ada."""
    response = client.delete("/products/999999")
    assert response.status_code == 404
