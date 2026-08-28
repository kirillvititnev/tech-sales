import { CartView } from "@/components/CartView";

export default function CartPage() {
  return <CartView checkoutHref="/checkout" catalogHref="/catalog" />;
}
