import { act, render, screen } from '@testing-library/react';
import { PriceCell } from '@/components/PriceCell';

describe('PriceCell', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('flashes up then clears', () => {
    const { rerender } = render(<PriceCell price={100} testId="p" />);
    expect(screen.getByTestId('p')).toHaveAttribute('data-flash', '');
    rerender(<PriceCell price={101} testId="p" />);
    expect(screen.getByTestId('p')).toHaveAttribute('data-flash', 'up');
    act(() => { vi.advanceTimersByTime(100); });
    expect(screen.getByTestId('p')).toHaveAttribute('data-flash', '');
  });

  it('flashes down on decrease', () => {
    const { rerender } = render(<PriceCell price={100} testId="p" />);
    rerender(<PriceCell price={99} testId="p" />);
    expect(screen.getByTestId('p')).toHaveAttribute('data-flash', 'down');
  });
});
