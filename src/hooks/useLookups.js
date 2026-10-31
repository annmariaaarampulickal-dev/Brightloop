import useFetch from './useFetch';
import { useAuth } from './useAuth';
import { listAllCustomers } from '../services/customerService';
import { listPlans, listProducts, listTaxes, listTemplates } from '../services/productService';

// Reference data used by dropdowns and to turn ids into names (the API returns ids only).
// Staff/admin get everything; a customer only needs plans (and their own name).
export default function useLookups() {
  const { user } = useAuth();
  const staff = user.role !== 'customer';
  const { data, loading, reload } = useFetch(
    () =>
      Promise.all([
        listPlans(),
        staff ? listAllCustomers() : Promise.resolve([]),
        staff ? listProducts() : Promise.resolve([]),
        staff ? listTaxes() : Promise.resolve([]),
        staff ? listTemplates() : Promise.resolve([]),
      ]),
    [user.id]
  );
  const [plans = [], customers = [], products = [], taxes = [], templates = []] = data || [];
  const byId = (arr) => Object.fromEntries(arr.map((x) => [x.id, x]));
  return {
    loading, reload, plans, customers, products, taxes, templates,
    plansById: byId(plans),
    productsById: byId(products),
    customersById: staff ? byId(customers) : { [user.id]: user },
  };
}
