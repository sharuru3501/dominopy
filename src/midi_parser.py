
from mido import MidiFile, Message, MetaMessage, MidiTrack as MidoTrack
from src.midi_data_model import MidiNote, MidiTrack, MidiProject
from typing import List

def load_midi_file(file_path: str) -> MidiProject:
    project = MidiProject()
    mid = MidiFile(file_path)

    project.ticks_per_beat = mid.ticks_per_beat

    # Process tempo and time signature messages from the first track (usually track 0)
    current_tick = 0
    for msg in mid.tracks[0]:
        current_tick += msg.time  # Update absolute tick position
        
        if isinstance(msg, MetaMessage):
            if msg.type == 'set_tempo':
                from src.midi_data_model import TempoChange
                tempo_change = TempoChange.from_microseconds(current_tick, msg.tempo)
                project.tempo_changes.append(tempo_change)
            elif msg.type == 'time_signature':
                from src.midi_data_model import TimeSignatureChange
                ts_change = TimeSignatureChange(current_tick, msg.numerator, msg.denominator)
                project.time_signature_changes.append(ts_change)

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


def save_midi_file(midi_project: MidiProject, file_path: str) -> bool:
    """
    Save a MidiProject to a MIDI file.
    
    Args:
        midi_project: The MidiProject to save
        file_path: Path where to save the MIDI file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create a new MIDI file
        mid = MidiFile(ticks_per_beat=midi_project.ticks_per_beat)
        
        # Create tempo and time signature track (track 0)
        meta_track = MidoTrack()
        
        # Add tempo changes
        current_tempo_tick = 0
        for tempo_change in midi_project.tempo_changes:
            tick = tempo_change.tick
            tempo = tempo_change.microseconds_per_beat  # MIDI tempo in microseconds per beat
            
            # Add delta time
            delta_time = tick - current_tempo_tick
            current_tempo_tick = tick
            
            # Create tempo meta message
            tempo_msg = MetaMessage('set_tempo', tempo=tempo, time=delta_time)
            meta_track.append(tempo_msg)
        
        # Add time signature changes
        current_ts_tick = 0
        for ts_change in midi_project.time_signature_changes:
            tick = ts_change.tick
            numerator = ts_change.numerator
            denominator = ts_change.denominator
            
            # Add delta time
            delta_time = tick - current_ts_tick
            current_ts_tick = tick
            
            # Create time signature meta message
            ts_msg = MetaMessage('time_signature', 
                               numerator=numerator, 
                               denominator=denominator,
                               time=delta_time)
            meta_track.append(ts_msg)
        
        # Add end of track message
        meta_track.append(MetaMessage('end_of_track', time=0))
        mid.tracks.append(meta_track)
        
        # Process each track
        for track_index, midi_track in enumerate(midi_project.tracks):
            if not midi_track.notes:
                continue  # Skip empty tracks
                
            mido_track = MidoTrack()
            
            # Create a list of all MIDI events (note_on and note_off) with their timestamps
            events = []
            
            for note in midi_track.notes:
                # Note on event
                events.append({
                    'tick': note.start_tick,
                    'type': 'note_on',
                    'note': note.pitch,
                    'velocity': note.velocity,
                    'channel': note.channel
                })
                
                # Note off event
                events.append({
                    'tick': note.end_tick,
                    'type': 'note_off',
                    'note': note.pitch,
                    'velocity': 64,  # Standard note off velocity
                    'channel': note.channel
                })
            
            # Sort events by tick
            events.sort(key=lambda x: x['tick'])
            
            # Convert absolute ticks to delta times and create MIDI messages
            current_tick = 0
            for event in events:
                delta_time = event['tick'] - current_tick
                current_tick = event['tick']
                
                if event['type'] == 'note_on':
                    msg = Message('note_on',
                                channel=event['channel'],
                                note=event['note'],
                                velocity=event['velocity'],
                                time=delta_time)
                elif event['type'] == 'note_off':
                    msg = Message('note_off',
                                channel=event['channel'],
                                note=event['note'],
                                velocity=event['velocity'],
                                time=delta_time)
                
                mido_track.append(msg)
            
            # Add end of track message
            mido_track.append(MetaMessage('end_of_track', time=0))
            mid.tracks.append(mido_track)
        
        # Save the MIDI file
        mid.save(file_path)
        return True
        
    except Exception as e:
        print(f"Error saving MIDI file: {e}")
        return False
