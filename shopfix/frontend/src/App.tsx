import { Route, Routes } from "react-router-dom";
import NavBar from "./components/NavBar";
import CartPage from "./pages/CartPage";
import HomePage from "./pages/HomePage";
import ListingPage from "./pages/ListingPage";
import LoginPage from "./pages/LoginPage";
import ShopDashboardPage from "./pages/ShopDashboardPage";

export default function App() {
  return (
    <>
      <NavBar />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/listing/:id" element={<ListingPage />} />
        <Route path="/cart" element={<CartPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/shop" element={<ShopDashboardPage />} />
      </Routes>
    </>
  );
}
