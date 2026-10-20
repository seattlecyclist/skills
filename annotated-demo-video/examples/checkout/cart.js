// Shared cart data and rendering for checkout.html (buggy) and checkout-fixed.html.
const ITEMS = [
  { name: "Trail Runner 2",  meta: "Men's 10 · Slate",   price: 120, qty: 1 },
  { name: "Merino Hike Sock", meta: "Medium · Charcoal",  price: 18,  qty: 3 },
  { name: "Ridgeline Cap",   meta: "One size · Moss",     price: 24,  qty: 2 },
];
const SHIPPING = 8;
const TAX_RATE = 0.10;
const money = n => "$" + n.toFixed(2);

function render(subtotalFn) {
  const list = document.getElementById("line-items");
  for (const item of ITEMS) {
    const li = document.createElement("li");
    li.innerHTML = `<div class="thumb"><span class="qty">${item.qty}</span></div>` +
      `<div><div class="name"></div><div class="meta"></div></div><div class="price"></div>`;
    li.querySelector(".name").textContent = item.name;
    li.querySelector(".meta").textContent = `${item.meta} · ${money(item.price)} each`;
    li.querySelector(".price").textContent = money(item.price * item.qty);
    list.appendChild(li);
  }
  const sub = subtotalFn(ITEMS);
  const tax = Math.round(sub * TAX_RATE * 100) / 100;
  document.getElementById("subtotal").textContent = money(sub);
  document.getElementById("shipping-cost").textContent = money(SHIPPING);
  document.getElementById("tax").textContent = money(tax);
  document.getElementById("total").textContent = money(sub + SHIPPING + tax);
}
