import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChatPanel } from '@/components/ChatPanel';

describe('ChatPanel', () => {
  it('renders messages with inline trade and watchlist confirmations', () => {
    render(<ChatPanel loading={false} onSend={vi.fn()} messages={[
      { id: '1', role: 'user', content: 'buy aapl' },
      { id: '2', role: 'assistant', content: 'Done', actions: {
        trades: [{ ticker: 'AAPL', side: 'buy', quantity: 5, price: 190 }, { ticker: 'TSLA', side: 'buy', quantity: 999, error: 'Insufficient cash' }],
        watchlist_changes: [{ ticker: 'PYPL', action: 'add' }] } },
    ]} />);
    expect(screen.getAllByTestId('chat-message')).toHaveLength(2);
    const trades = screen.getAllByTestId('chat-trade-action');
    expect(trades[0]).toHaveTextContent('Bought 5 AAPL @ 190.00');
    expect(trades[1]).toHaveTextContent('Trade failed');
    expect(screen.getByTestId('chat-watchlist-action')).toHaveTextContent('Added PYPL to watchlist');
  });
  it('shows loading indicator', () => {
    render(<ChatPanel loading messages={[]} onSend={vi.fn()} />);
    expect(screen.getByTestId('chat-loading')).toBeInTheDocument();
  });
  it('sends and clears input', async () => {
    const onSend = vi.fn();
    render(<ChatPanel loading={false} messages={[]} onSend={onSend} />);
    await userEvent.type(screen.getByTestId('chat-input'), 'hello');
    await userEvent.click(screen.getByTestId('chat-send'));
    expect(onSend).toHaveBeenCalledWith('hello');
    expect(screen.getByTestId('chat-input')).toHaveValue('');
  });
});
