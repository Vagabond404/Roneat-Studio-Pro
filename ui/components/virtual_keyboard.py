import customtkinter as ctk

class VirtualRoneatKeyboard(ctk.CTkFrame):
    """
    Virtual Roneat Keyboard UI component.
    """
    def __init__(self, master, step_controller=None, on_insert_callback=None, **kwargs):
        super().__init__(master, **kwargs)
        self.step_controller = step_controller
        self.on_insert_callback = on_insert_callback
        
        # Example UI for the virtual keyboard (placeholder)
        self.grid_columnconfigure(0, weight=1)
        self.label = ctk.CTkLabel(self, text="Virtual Roneat Keyboard")
        self.label.grid(row=0, column=0, pady=10)
        
        self.bars_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.bars_frame.grid(row=1, column=0, pady=10)
        
        # Create some clickable bars as placeholder
        for i in range(1, 22):
            btn = ctk.CTkButton(
                self.bars_frame, 
                text=str(i), 
                width=30,
                command=lambda pitch=i: self._on_bar_clicked(pitch)
            )
            btn.grid(row=0, column=i, padx=2)

    def set_step_controller(self, controller):
        """Bind the StepEntryController to this keyboard."""
        self.step_controller = controller

    def _on_bar_clicked(self, pitch_index: int):
        """
        Handle bar click events. Fetches duration from StepEntryController
        and generates the corresponding NoteEvent or Rest.
        """
        if self.step_controller:
            # 3. Bind Input to Controller: Fetch the currently selected duration
            duration = self.step_controller.selected_duration
            
            # 4. Generate and Append Note: 
            # The controller handles creating a Rest or NoteEvent and advancing cursor
            event_result = self.step_controller.insert_step_note(pitch_index)
            
            if self.on_insert_callback:
                self.on_insert_callback(pitch_index, self.step_controller.is_rest_active)
            
            print(f"[VirtualRoneatKeyboard] Clicked {pitch_index}. Generated: {event_result}")
        else:
            print(f"[VirtualRoneatKeyboard] Clicked {pitch_index}, but no StepEntryController bound.")

