import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { checkout, fetchCart, formatPrice } from "../api/client";

type CartData = Awaited<ReturnType<typeof fetchCart>>;

export default function CartPage() {
  const [cart, setCart] = useState<CartData | null>(null);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    fetchCart()
      .then(setCart)
      .catch(() => setMsg("Log in to view your cart"));
  }, []);

  async function onCheckout() {
    try {
      await checkout();
      setMsg("Order placed!");
      setCart({ items: [], total_cents: 0 });
    } catch {
      setMsg("Checkout failed");
    }
  }

  if (!cart) return <div className="container">{msg || "Loading…"}</div>;

  return (
    <div className="container">
      <h1>Your cart</h1>
      {cart.items.length === 0 ? (
        <p>
          Cart is empty. <Link to="/">Browse listings</Link>
        </p>
      ) : (
        <>
          <ul>
            {cart.items.map((item) => (
              <li key={item.listing.id}>
                {item.listing.title} × {item.quantity} — {formatPrice(item.listing.price_cents * item.quantity)}
              </li>
            ))}
          </ul>
          <p className="price">Total: {formatPrice(cart.total_cents)}</p>
          <button type="button" onClick={onCheckout}>
            Checkout
          </button>
        </>
      )}
      {msg && <p>{msg}</p>}
    </div>
  );
}
