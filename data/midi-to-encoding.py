import os
import numpy as np
from math import floor
import music21
from pathlib import Path


def stream_to_chordwise(s, chamber, note_range, note_offset, sample_freq):
    maxTimeStep = floor(s.duration.quarterLength * sample_freq) + 1
    score_arr = np.zeros((maxTimeStep, 1, note_range))

    notes = []
    instrumentID = 0

    noteFilter = music21.stream.filters.ClassFilter('Note')
    chordFilter = music21.stream.filters.ClassFilter('Chord')

    for n in s.recurse().addFilter(noteFilter):
        notes.append((n.pitch.midi - note_offset, floor(n.offset * sample_freq),
                      floor(n.duration.quarterLength * sample_freq), instrumentID))

    for c in s.recurse().addFilter(chordFilter):
        pitchesInChord = c.pitches

        for p in pitchesInChord:
            notes.append((p.midi - note_offset, floor(c.offset * sample_freq),
                          floor(c.duration.quarterLength * sample_freq), instrumentID))

    for n in notes:
        pitch = n[0]
        while pitch < 0:
            pitch += 12
        while pitch >= note_range:
            pitch -= 12

        score_arr[n[1], n[3], pitch] = 1                  # Strike note
        # Continue holding note
        score_arr[n[1] + 1:n[1] + n[2], n[3], pitch] = 2

    instr = {}
    instr[0] = "p"
    score_string_arr = []
    for timestep in score_arr:
        # List violin note first, then piano note
        for i in list(reversed(range(len(timestep)))):
            score_string_arr.append(
                instr[i] + ''.join([str(int(note)) for note in timestep[i]]))

    return score_string_arr


def add_modulations(score_string_arr):
    modulated = []
    note_range = len(score_string_arr[0]) - 1
    for i in range(0, 12):
        for chord in score_string_arr:
            padded = '000000' + chord[1:] + '000000'
            modulated.append(chord[0] + padded[i:i + note_range])
    return modulated


def chord_to_notewise(long_string, sample_freq):
    translated_list = []
    for j in range(len(long_string)):
        chord = long_string[j]
        next_chord = ""
        for k in range(j + 1, len(long_string)):
            if long_string[k][0] == chord[0]:
                next_chord = long_string[k]
                break
        prefix = chord[0]
        chord = chord[1:]
        next_chord = next_chord[1:]
        for i in range(len(chord)):
            if chord[i] == "0":
                continue
            note = prefix + str(i)
            if chord[i] == "1":
                translated_list.append(note)
            # If chord[i]=="2" do nothing - we're continuing to hold the note
            # unless next_chord[i] is back to "0" and it's time to end the note.
            if next_chord == "" or next_chord[i] == "0":
                translated_list.append("end" + note)

        if prefix == "p":
            translated_list.append("wait")

    i = 0
    translated_string = ""
    while i < len(translated_list):
        wait_count = 1
        if translated_list[i] == 'wait':
            while wait_count <= sample_freq * 2 and i + wait_count < len(translated_list) and translated_list[i + wait_count] == 'wait':
                wait_count += 1
            translated_list[i] = 'wait' + str(wait_count)
        translated_string += translated_list[i] + " "
        i += wait_count

    return translated_string


def translate_folder_path(START_PATH, note_range, sample_freq, composer):
    note_range_folder = "note_range" + str(note_range)
    sample_freq_folder = "sample_freq" + str(sample_freq)
    directory = START_PATH / note_range_folder / sample_freq_folder / composer
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def translate_piece(fname, composer, sample_freqs, note_ranges, note_offsets, CHORDWISE_PATH, NOTEWISE_PATH):
    for sample_freq in sample_freqs:
        for note_range in note_ranges:
            notewise_directory = translate_folder_path(
                NOTEWISE_PATH, note_range, sample_freq, composer)
            chordwise_directory = translate_folder_path(
                CHORDWISE_PATH, note_range, sample_freq, composer)

    mf = music21.midi.MidiFile()
    print(f"fname: {fname}")
    try:
        mf.open(fname)
        mf.read()
        mf.close()
    except:
        print("Skipping file: Midi file has bad formatting")
        return

    print("Waiting for MIT music21.midi.translate.midiFileToStream()")
    try:
        midi_stream = music21.midi.translate.midiFileToStream(mf)
    except:
        print("Skipping file: music21.midi.translate failed")
        return
    print("Translating stream to encodings")

    for sample_freq in sample_freqs:
        for note_range in note_ranges:

            score_string_arr = stream_to_chordwise(
                midi_stream, note_range, note_offsets[note_range], sample_freq)
            if len(score_string_arr) == 0:
                print("Skipping file: Unknown instrument")
                return

            score_string_arr = add_modulations(score_string_arr)

            chordwise_directory = translate_folder_path(
                CHORDWISE_PATH, note_range, sample_freq, composer)
            os.chdir(chordwise_directory)

            f = open(fname[:-4] + ".txt", "w+")
            f.write(" ".join(score_string_arr))
            f.close()

            # Translate to notewise format
            score_string = chord_to_notewise(score_string_arr, sample_freq)

            # Write notewise format to file
            notewise_directory = translate_folder_path(
                NOTEWISE_PATH, note_range, sample_freq, composer)
            os.chdir(notewise_directory)

            f = open(fname[:-4] + ".txt", "w+")
            f.write(score_string)
            f.close()
    print("Success")


def main():
    BASE_PATH = Path(os.path.dirname(os.path.realpath(__file__)))

    ABBA_PATH = BASE_PATH / 'abba'
    CHORDWISE_PATH = BASE_PATH / 'chordwise'
    NOTEWISE_PATH = BASE_PATH / 'notewise'

    sample_freqs = [4, 12]
    note_ranges = [38, 62]
    note_offsets = {}
    note_offsets[38] = 45
    note_offsets[62] = 33

    output_folder = BASE_PATH
    fname = ABBA_PATH / 'abba_-_dancing_queen.mid'

    mf = music21.midi.MidiFile()
    print(f"fname: {fname}")
    try:
        mf.open(fname)
        mf.read()
        mf.close()
    except Exception as e:
        print(e)
        print("Skipping file: Midi file has bad formatting")
        return

    print(mf)

    # translate_piece(fname, output_folder, sample_freqs,
    #                 note_ranges, note_offsets, CHORDWISE_PATH, NOTEWISE_PATH)


if __name__ == "__main__":
    main()
