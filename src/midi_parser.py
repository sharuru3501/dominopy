
from mido import MidiFile, Message, MetaMessage
from src.midi_data_model import MidiNote, MidiTrack, MidiProject

def load_midi_file(file_path: str) -> MidiProject:
    project = MidiProject()
    mid = MidiFile(file_path)

    project.ticks_per_beat = mid.ticks_per_beat

    # Process tempo and time signature messages from the first track (usually track 0)
    for msg in mid.tracks[0]:
        if isinstance(msg, MetaMessage):
            if msg.type == 'set_tempo':
                project.tempo_map.append({'tick': msg.time, 'tempo': msg.tempo})
            elif msg.type == 'time_signature':
                project.time_signature_map.append({
                    'tick': msg.time,
                    'numerator': msg.numerator,
                    'denominator': msg.denominator
                })

    # Process notes for each track
    for i, track in enumerate(mid.tracks):
        new_track = MidiTrack(name=f"Track {i}")
        # Keep track of note_on messages to find corresponding note_off
        note_on_events = {} # {pitch: {channel: tick}}

        current_tick = 0
        for msg in track:
            current_tick += msg.time # mido message.time is delta time

            if msg.type in ['note_on', 'note_off']:
                if msg.type == 'note_on':
                    if msg.velocity > 0:
                        # Store note_on event with its velocity
                        if msg.note not in note_on_events:
                            note_on_events[msg.note] = {}
                        note_on_events[msg.note][msg.channel] = {'start_tick': current_tick, 'velocity': msg.velocity}
                    else: # msg.velocity == 0, treated as note_off
                        # Find corresponding note_on and create MidiNote
                        if msg.note in note_on_events and msg.channel in note_on_events[msg.note]:
                            start_tick = note_on_events[msg.note][msg.channel]['start_tick']
                            velocity = note_on_events[msg.note][msg.channel]['velocity']
                            note = MidiNote(
                                pitch=msg.note,
                                start_tick=start_tick,
                                end_tick=current_tick,
                                velocity=velocity,
                                channel=msg.channel
                            )
                            new_track.notes.append(note)
                            del note_on_events[msg.note][msg.channel]
                            if not note_on_events[msg.note]:
                                del note_on_events[msg.note]
                elif msg.type == 'note_off':
                    # Find corresponding note_on and create MidiNote
                    if msg.note in note_on_events and msg.channel in note_on_events[msg.note]:
                        start_tick = note_on_events[msg.note][msg.channel]['start_tick']
                        velocity = note_on_events[msg.note][msg.channel]['velocity']
                        note = MidiNote(
                            pitch=msg.note,
                            start_tick=start_tick,
                            end_tick=current_tick,
                            velocity=velocity,
                            channel=msg.channel
                        )
                        new_track.notes.append(note)
                        del note_on_events[msg.note][msg.channel]
                        if not note_on_events[msg.note]:
                            del note_on_events[msg.note]
            # else: ignore other message types for now (e.g., control_change, program_change, pitchwheel, meta_message)
        project.add_track(new_track)

    return project
