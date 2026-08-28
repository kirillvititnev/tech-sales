import { CartView } from "@/components/CartView";

export default function MiniCartPage() {
  return (
    <CartView checkoutHref="/mini/checkout" catalogHref="/mini" />
  );
}
