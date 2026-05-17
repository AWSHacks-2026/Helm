import { Link } from "react-router-dom";

export default function NavBar() {
  const loggedIn = !!localStorage.getItem("shopfix_token");
  return (
    <nav className="nav">
      <Link to="/" className="brand">
        ShopFix
      </Link>
      <Link to="/">Browse</Link>
      <Link to="/cart">Cart</Link>
      <Link to="/shop">My shop</Link>
      {loggedIn ? (
        <button
          type="button"
          onClick={() => {
            localStorage.removeItem("shopfix_token");
            window.location.href = "/";
          }}
        >
          Log out
        </button>
      ) : (
        <Link to="/login">Log in</Link>
      )}
    </nav>
  );
}
