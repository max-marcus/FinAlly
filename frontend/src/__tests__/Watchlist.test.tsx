import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Watchlist } from '@/components/Watchlist';

const items = [{ ticker: 'AAPL', price: 190 }, { ticker: 'MSFT', price: 400 }];
const prices = { AAPL: { ticker: 'AAPL', price: 191, previous_price: 190, timestamp: 1, change: 1, change_percent: 0.52, direction: 'up' as const } };

function setup(over: Partial<Parameters<typeof Watchlist>[0]> = {}) {
  const props = { items, prices, history: { AAPL: [1, 2, 3] }, selected: 'AAPL', onSelect: vi.fn(), onAdd: vi.fn().mockResolvedValue(undefined), onRemove: vi.fn().mockResolvedValue(undefined), ...over };
  render(<Watchlist {...props} />);
  return props;
}

describe('Watchlist', () => {
  it('renders rows with live price', () => {
    setup();
    expect(screen.getByTestId('watchlist-row-AAPL')).toBeInTheDocument();
    expect(screen.getByTestId('price-AAPL')).toHaveTextContent('191.00');
    expect(screen.getByTestId('price-MSFT')).toHaveTextContent('400.00');
  });
  it('selects on click', async () => {
    const p = setup();
    await userEvent.click(screen.getByTestId('watchlist-row-MSFT'));
    expect(p.onSelect).toHaveBeenCalledWith('MSFT');
  });
  it('adds an upper-cased ticker', async () => {
    const p = setup();
    await userEvent.type(screen.getByTestId('watchlist-input'), 'pypl');
    await userEvent.click(screen.getByTestId('watchlist-add'));
    expect(p.onAdd).toHaveBeenCalledWith('PYPL');
  });
  it('shows add errors', async () => {
    setup({ onAdd: vi.fn().mockRejectedValue(new Error('Unknown ticker')) });
    await userEvent.type(screen.getByTestId('watchlist-input'), 'zzz');
    await userEvent.click(screen.getByTestId('watchlist-add'));
    await waitFor(() => expect(screen.getByTestId('watchlist-error')).toHaveTextContent('Unknown ticker'));
  });
  it('removes without selecting', async () => {
    const p = setup();
    await userEvent.click(screen.getByTestId('remove-MSFT'));
    expect(p.onRemove).toHaveBeenCalledWith('MSFT');
    expect(p.onSelect).not.toHaveBeenCalled();
  });
});
