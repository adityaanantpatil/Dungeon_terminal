import json
import ollama
from pydantic import BaseModel
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text

# Initialize Rich Console for beautiful terminal output
console = Console()

# ---------------------------------------------------------
# 1. DEFINE THE AI'S OUTPUT STRUCTURE
# ---------------------------------------------------------
class TurnOutcome(BaseModel):
    narration: str
    hp_change: int
    added_items: list[str]
    removed_items: list[str]
    is_game_over: bool

class DungeonMasterRPG:
    def __init__(self):
        # State Management (Memory)
        self.hp = 100
        self.inventory = ["Lint", "Mysterious Coin"]
        self.history = [] 
        
        # We define the local model we downloaded via Ollama
        self.model_id = 'llama3.2' 
        
        self.system_instruction = """
        You are a ruthless but fair Dungeon Master running a dark fantasy text adventure.
        You must process the player's action, roll virtual dice behind the scenes to 
        determine success or failure, and output the consequences. 
        Be descriptive, atmospheric, and concise. Keep narration to 2-3 sentences.
        You MUST return your response as a valid JSON object matching the provided schema.
        """

    def generate_starting_scenario(self):
        prompt = "Generate a gripping, atmospheric starting scenario for the player. They are waking up in a dangerous, unknown location."
        
        response = ollama.chat(
            model=self.model_id,
            messages=[
                {'role': 'system', 'content': self.system_instruction},
                {'role': 'user', 'content': prompt}
            ],
            # Force Ollama to return exactly this JSON structure
            format=TurnOutcome.model_json_schema(), 
            options={'temperature': 0.8}
        )
        
        # Parse the JSON string returned by Ollama into our Python object
        return TurnOutcome.model_validate_json(response['message']['content'])

    def process_turn(self, user_action):
        context = "\n".join(self.history[-4:]) 
        
        prompt = f"""
        Recent History:
        {context}
        
        Current Player State:
        HP: {self.hp}/100
        Inventory: {', '.join(self.inventory) if self.inventory else 'Empty'}
        
        Player Action: "{user_action}"
        
        Evaluate the action based on the current state and inventory. 
        Apply consequences. 
        """
        
        response = ollama.chat(
            model=self.model_id,
            messages=[
                {'role': 'system', 'content': self.system_instruction},
                {'role': 'user', 'content': prompt}
            ],
            format=TurnOutcome.model_json_schema(),
            options={'temperature': 0.7}
        )
        
        return TurnOutcome.model_validate_json(response['message']['content'])

    def update_state(self, outcome: TurnOutcome):
        self.hp += outcome.hp_change
        if self.hp > 100: self.hp = 100
        if self.hp < 0: self.hp = 0
        
        for item in outcome.added_items:
            if item not in self.inventory:
                self.inventory.append(item)
                
        for item in outcome.removed_items:
            if item in self.inventory:
                self.inventory.remove(item)

    def render_ui(self, narration):
        console.clear()
        
        hp_color = "green" if self.hp > 50 else "yellow" if self.hp > 20 else "red"
        stats_text = Text(f"HP: {self.hp}/100 | Inventory: {', '.join(self.inventory)}", style=f"bold {hp_color}")
        console.print(Panel(stats_text, title="Character Stats", border_style="cyan"))
        
        console.print(Panel(narration, title="The Story So Far", border_style="green"))

    def play(self):
        console.clear()
        with console.status("[bold green]The Local Dungeon Master is waking up..."):
            outcome = self.generate_starting_scenario()
        
        self.history.append(f"DM: {outcome.narration}")
        self.render_ui(outcome.narration)
        
        while not outcome.is_game_over and self.hp > 0:
            action = Prompt.ask("\n[bold yellow]What do you do?[/bold yellow]")
            
            if action.lower() in ['quit', 'exit']:
                console.print("[bold red]You abandon your quest.[/bold red]")
                break
            
            self.history.append(f"Player: {action}")
            
            with console.status("[bold green]The DM rolls the dice..."):
                outcome = self.process_turn(action)
            
            self.history.append(f"DM: {outcome.narration}")
            self.update_state(outcome)
            self.render_ui(outcome.narration)
            
            if outcome.hp_change < 0:
                console.print(f"[bold red]You took {abs(outcome.hp_change)} damage![/bold red]")
            elif outcome.hp_change > 0:
                console.print(f"[bold green]You healed {outcome.hp_change} HP![/bold green]")
                
            for item in outcome.added_items:
                console.print(f"[bold yellow]+ Acquired: {item}[/bold yellow]")
            for item in outcome.removed_items:
                console.print(f"[bold dark_orange]- Lost: {item}[/bold dark_orange]")

        if self.hp <= 0 or outcome.is_game_over:
            console.print("\n[bold red on black] GAME OVER [/bold red on black]")

if __name__ == "__main__":
    game = DungeonMasterRPG()
    game.play()