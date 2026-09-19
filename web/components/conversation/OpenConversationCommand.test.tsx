import { fireEvent, render, screen } from '@testing-library/react';
import { OpenConversationCommand } from './OpenConversationCommand';

describe('OpenConversationCommand', () => {
  it('dispatches the opener element for focus restoration', () => {
    const listener = jest.fn();
    window.addEventListener('waooaw:open-conversation', listener);
    render(<OpenConversationCommand label="Ask about this professional" />);

    const button = screen.getByRole('button', { name: 'Ask about this professional' });
    fireEvent.click(button);

    expect(listener).toHaveBeenCalledTimes(1);
    expect((listener.mock.calls[0][0] as CustomEvent).detail).toEqual({ opener: button });
    window.removeEventListener('waooaw:open-conversation', listener);
  });
});
