from fasthtml.common import *
from index import agent
from pydantic import BaseModel
from pydantic_ai import Agent
import logfire
from dotenv import load_dotenv
import re
import html

# UI for AI Agent Chat
# - Renders the chat interface and product "cards"
# - Handles HTMX-driven form submissions and out-of-band updates
# - Parses special card-action tags in agent responses to add/remove cards

load_dotenv(override=True)
logfire.configure()
logfire.instrument_pydantic_ai()

model = "google-gla:gemini-2.5-flash"

# Pydantic model for Card
class Card(BaseModel):
    title: str
    color: str
    quantity: int = 1

# Dictionary to store all cards
all_cards = {}

app, routes = fast_app(
    hdrs=(Script(src="https://cdn.tailwindcss.com"),), 
    pico=False
)

all_messages = []

@routes("/")
def index():
    return Title("Agent App"), Div(
        # Main container with two columns
        Div(
            # Left side - Chat area
            Div(
                # Header
                H1(
                    "Agent App",
                    cls="text-5xl font-bold text-blue-600 mb-1"
                ),
                
                # Form
                Form(
                    Div(
                        Input(
                            id="msg",
                            name="msg",
                            placeholder="Type your message...",
                            cls="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                        ),
                        Button(
                            "Send",
                            type="submit",
                            id="send-btn",
                            cls="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-semibold shadow-md"
                        ),
                        cls="flex gap-3"
                    ),
                    id="form",
                    cls="bg-white rounded-xl p-6 shadow-lg",
                    hx_post="/echo",
                    hx_target="#messages",
                    hx_swap="beforeend"
                ),

                # Product Cards moved below the input/send form
                Div(
                    Div(
                        H2(
                            "Cards Section",
                            cls="text-2xl font-bold text-white mb-6 text-center"
                        ),
                        Div(
                            P(
                                "No cards yet. Try adding one!",
                                cls="text-gray-400 text-center italic py-4"
                            ),
                            id="card-zone",
                            cls="space-y-4 overflow-y-auto"
                        ),
                        cls="sticky top-8 bg-gradient-to-br from-gray-800 to-gray-900 bg-gray-800/80 rounded-xl p-6 shadow-2xl border-2 border-gray-700 min-h-full"
                    ),
                    cls="w-full px-4 py-8 mt-6"
                ),
                
                cls="flex-1 px-4 py-8 w-full"
            ),
            
            # (Product Cards moved into left column)
            
            cls="flex max-w-7xl mx-auto"
        ),
        
        Script("""
            /*
             Client-side behavior for the chat UI:
             - Track an `apiPending` flag to avoid duplicate requests.
             - Disable the send button when input is empty or a request is pending.
             - Provide a visual disabled state (opacity + not-allowed cursor).
             - Support Enter to send (Shift+Enter inserts a newline).
             - Use HTMX events to reset state after requests complete.
            */

            let apiPending = false;
            const form = document.getElementById('form');

            // Toggle disabled state and visual classes on the send button
            function applyButtonDisabled(disabled) {
                if (!form) return;
                let btn = form.querySelector('#send-btn');
                if (!btn) btn = form.querySelector('button[type=submit]');
                if (!btn) return;
                btn.disabled = disabled;
                if (disabled) {
                    // Make disabled button look and behave disabled
                    btn.classList.add('opacity-50', 'cursor-not-allowed', 'bg-gray-400');
                    btn.classList.remove('bg-blue-600', 'hover:bg-blue-700');
                } else {
                    btn.classList.remove('opacity-50', 'cursor-not-allowed', 'bg-gray-400');
                    btn.classList.add('bg-blue-600', 'hover:bg-blue-700');
                }
            }

            // Enable/disable depending on whether input contains non-whitespace text
            function updateSubmitState() {
                const input = document.getElementById('msg');
                const empty = !input || !input.value.trim();
                applyButtonDisabled(apiPending || empty);
            }

            // Prevent submission when input is empty, otherwise mark as pending
            if (form) {
                form.addEventListener('submit', function(e) {
                    const input = document.getElementById('msg');
                    if (!input || !input.value.trim()) {
                        e.preventDefault();
                        updateSubmitState();
                        if (input) input.focus();
                        return;
                    }
                    apiPending = true;
                    applyButtonDisabled(true);
                });
            }

            // HTMX fires afterRequest for each request — clear pending and update UI
            document.body.addEventListener('htmx:afterRequest', function(evt) {
                apiPending = false;
                updateSubmitState();
            });

            // After HTMX swaps content into the page: clear input and scroll messages
            document.body.addEventListener('htmx:afterSwap', function(evt) {
                const input = document.getElementById('msg');
                if (input) input.value = '';
                const messages = document.getElementById('messages');
                if (messages) messages.scrollTop = messages.scrollHeight;
                apiPending = false;
                updateSubmitState();
            });

            // Enter sends the message (unless Shift is held); prevent empty or pending sends
            const msgInput = document.getElementById('msg');
            if (msgInput) {
                msgInput.addEventListener('keydown', function(e) {
                    if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        if (apiPending) return;
                        if (!msgInput.value || !msgInput.value.trim()) {
                            msgInput.focus();
                            updateSubmitState();
                            return;
                        }
                        const formEl = document.getElementById('form');
                        if (formEl) {
                            if (typeof formEl.requestSubmit === 'function') {
                                formEl.requestSubmit();
                            } else {
                                const btn = formEl.querySelector('button[type=submit]');
                                if (btn) btn.click();
                            }
                        }
                    }
                });

                // Update the button enabled/disabled state while typing
                msgInput.addEventListener('input', function() {
                    updateSubmitState();
                });
            }

            // Initialize the button state on page load
            updateSubmitState();
        """),
        
        cls="min-h-screen bg-gray-100"
    )

def render_all_cards():
    """Render all cards from the all_cards dictionary"""
    if not all_cards:
        # Return empty state message
        return [P(
            "No cards yet. Try adding one!",
            cls="text-gray-400 text-center italic py-4"
        )]
    
    card_elements = []
    for title, card in all_cards.items():
        card_element = Div(
            H3(f"{card.title}", cls="text-xl font-bold mb-1 text-center"),
            P(f"Quantity: {card.quantity}", cls="text-sm text-center opacity-90"),
            cls=f"px-6 py-8 rounded-xl shadow-xl {card.color} text-white flex flex-col items-center justify-center hover:scale-105 transition-all duration-300 cursor-pointer border-2 border-white border-opacity-30",
            id=f"card-{title.lower().replace(' ', '-')}"
        )
        card_elements.append(card_element)
    return card_elements

@routes("/echo")
async def post(msg: str = ""):
    global all_messages, all_cards
    
    user_msg = msg.strip() or "(empty)"
    
    # Get agent response
    response = await agent.run(user_msg, message_history=all_messages)
    all_messages = response.all_messages()
    agent_response = response.output
    
    # Parse agent response for embedded card-action tags.
    # Tag format (case-insensitive, whitespace tolerant):
    #   [CARD_ACTION:ADD|TITLE:product name|QUANTITY:3]
    # or
    #   [CARD_ACTION:REMOVE|TITLE:product name|QUANTITY:ALL]
    # We accept small formatting variations and remove the tag before display.
    card_action_match = re.search(
        r'\[CARD_ACTION\s*:\s*(ADD|REMOVE)\s*\|\s*TITLE\s*:\s*([^|]+?)\s*\|\s*QUANTITY\s*:\s*(ALL|\d+)\s*\]',
        agent_response,
        re.I
    )

    # Remove the card action tag from the displayed response (case-insensitive).
    display_response = re.sub(r'\[CARD_ACTION[^\]]+\]\s*', '', agent_response, flags=re.I).strip()

    # HTML-escape the cleaned response to prevent XSS, and use whitespace-aware
    # classes in the UI so the original newline formatting is preserved.
    agent_text = html.escape(display_response)
    
    # User message bubble (right side, blue)
    user_bubble = Div(
        Div(
            P("You", cls="text-xs text-blue-600 font-bold mb-1"),
            P(user_msg, cls="text-white"),
            cls="inline-block bg-blue-500 px-4 py-3 rounded-2xl rounded-tr-sm max-w-md shadow-md"
        ),
        cls="flex justify-end mb-3"
    )
    
    # Agent message bubble (left side, green) - show the escaped, formatted text
    agent_bubble = Div(
        Div(
            P("Agent", cls="text-xs text-green-600 font-bold mb-1"),
            P(agent_text, cls="text-gray-800 whitespace-pre-wrap break-words"),
            cls="inline-block bg-green-100 px-4 py-3 rounded-2xl rounded-tl-sm max-w-md shadow-md border border-green-300"
        ),
        cls="flex justify-start mb-3"
    )
    
    # Process the parsed card action (if any). Actions mutate `all_cards`.
    if card_action_match:
        action = card_action_match.group(1)
        card_title = card_action_match.group(2).strip()
        quantity_str = card_action_match.group(3)
        
        if action == "ADD":
            try:
                quantity = int(quantity_str)
            except Exception:
                quantity = 1
            # Check if card already exists
            if card_title in all_cards:
                # Increment quantity
                all_cards[card_title].quantity += quantity
                print(f"➕ Incremented quantity for card: {card_title} by {quantity} (now {all_cards[card_title].quantity})")
            else:
                # Ask the agent to choose a Tailwind CSS background color for the card.
                # We pass the same conversation history to keep the response relevant.
                color_prompt = f"What Tailwind CSS background color class (like bg-yellow-400, bg-red-500, bg-blue-600, etc.) best represents '{card_title}'? Reply with ONLY the class name (e.g., bg-yellow-400)."
                color_response = await agent.run(color_prompt, message_history=all_messages)
                agent_color = color_response.output.strip()
                
                # Validate that it's a valid Tailwind color class
                if agent_color.startswith("bg-") and "-" in agent_color:
                    card_color = agent_color
                else:
                    # Fallback colors if agent doesn't return valid format
                    card_color = "bg-blue-500"
                
                # Create Card model and add to dictionary
                new_card = Card(title=card_title, color=card_color, quantity=quantity)
                all_cards[card_title] = new_card
                print(f"➕ Added card: {card_title} with color {card_color} and quantity {quantity}")
            
            print(f"📋 All cards: {all_cards}")
            
        elif action == "REMOVE":
            if card_title in all_cards:
                if quantity_str == "ALL":
                    # Remove all quantity
                    del all_cards[card_title]
                    print(f"🗑️ Deleted ALL {card_title} cards!")
                else:
                    quantity = int(quantity_str)
                    # Decrease quantity or remove card
                    if all_cards[card_title].quantity > quantity:
                        all_cards[card_title].quantity -= quantity
                        print(f"➖ Decremented quantity for card: {card_title} by {quantity} (now {all_cards[card_title].quantity})")
                    else:
                        # Remove the card completely
                        del all_cards[card_title]
                        print(f"🗑️ Deleted card: {card_title}")
                
                print(f"📋 All cards: {all_cards}")
        
        # Re-render all cards from dictionary
        updated_card_zone = Div(
            *render_all_cards(),
            id="card-zone",
            cls="space-y-4 overflow-y-auto",
            hx_swap_oob="true"
        )
        
        return Div(user_bubble, agent_bubble, updated_card_zone)
    
    # Return both bubbles without card update
    return user_bubble, agent_bubble
serve(port=8000)