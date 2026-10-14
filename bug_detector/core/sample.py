"""Beispielcode für den Button „Beispiel“."""

SAMPLE_NAME = "beispiel.js"

SAMPLE_CODE = """// Beispiel: Warenkorb-Widget
var cart = [];
var unusedTotal = 0;

function load(input) {
  const data = eval(input);
  if (data.length == 0) {
    console.log("leer");
  }
  return data;
}

const API_KEY = "sk-demo-12345678";

function startPolling(el) {
  setInterval(function () {
    el.innerHTML = "Update: " + Date.now();
  }, 1000);
  window.addEventListener("resize", function () { render(); });
}

try { load("[]"); } catch (e) {}

function render() {
  if (cart.length > 0 {
    return cart;
  }
}
"""
