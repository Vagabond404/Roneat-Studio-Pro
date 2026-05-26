import customtkinter as ctk

class StepEntryController:
    def __init__(self):
        self.selected_duration = "Quarter"
        self.is_rest_active = False
        self.current_input_position = 0.0  # Placeholder for cursor management

    def set_duration(self, duration: str):
        self.selected_duration = duration

    def set_rest_active(self, is_active: bool):
        self.is_rest_active = is_active

    def insert_step_note(self, pitch_index: int):
        duration = self.selected_duration
        is_rest = self.is_rest_active
        
        # Cursor management placeholder
        # Increment current_input_position based on duration
        duration_values = {
            "Whole": 4.0,
            "Half": 2.0,
            "Quarter": 1.0,
            "Eighth": 0.5,
            "Sixteenth": 0.25
        }
        val = duration_values.get(duration, 1.0)
        self.current_input_position += val

        if is_rest:
            return f"Rest({duration})"
        else:
            return f"NoteEvent(pitch={pitch_index}, duration={duration})"


class RhythmToolbarFrame(ctk.CTkFrame):
    def __init__(self, master, controller: StepEntryController, **kwargs):
        super().__init__(master, **kwargs)
        self.controller = controller

        self.duration_var = ctk.StringVar(value="Quarter")
        self.rest_var = ctk.BooleanVar(value=False)

        # Durations
        durations = [
            ("Whole", "Rond"),
            ("Half", "Blanche"),
            ("Quarter", "Noire"),
            ("Eighth", "Croche"),
            ("Sixteenth", "Double-croche")
        ]

        # UI Layout
        self.grid_columnconfigure(tuple(range(len(durations) + 1)), weight=1)

        for i, (dur_val, label) in enumerate(durations):
            rb = ctk.CTkRadioButton(
                self,
                text=label,
                variable=self.duration_var,
                value=dur_val,
                command=self._on_duration_change
            )
            rb.grid(row=0, column=i, padx=5, pady=5)

        # Rest toggle
        self.rest_checkbox = ctk.CTkCheckBox(
            self,
            text="Rest (Silence)",
            variable=self.rest_var,
            command=self._on_rest_change
        )
        self.rest_checkbox.grid(row=0, column=len(durations), padx=5, pady=5)

    def _on_duration_change(self):
        self.controller.set_duration(self.duration_var.get())

    def _on_rest_change(self):
        self.controller.set_rest_active(self.rest_var.get())

