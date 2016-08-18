# Copyright 2016 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Defines sequence of notes objects for creating datasets.
"""

import collections

# Set the quantization cutoff.
# Note events before this cutoff are rounded down to nearest step. Notes
# above this cutoff are rounded up to nearest step. The cutoff is given as a
# fraction of a step.
# For example, with quantize_cutoff = 0.75 using 0-based indexing,
# if .75 < event <= 1.75, it will be quantized to step 1.
# If 1.75 < event <= 2.75 it will be quantized to step 2.
# A number close to 1.0 gives less wiggle room for notes that start early,
# and they will be snapped to the previous step.
QUANTIZE_CUTOFF = 0.5


class BadNoteException(Exception):
  pass


class BadTimeSignatureException(Exception):
  pass


class MultipleTimeSignatureException(Exception):
  pass


def is_power_of_2(x):
  return x and not x & (x - 1)


Note = collections.namedtuple(
    'Note', ['pitch', 'velocity', 'start', 'end', 'instrument', 'program'])
TimeSignature = collections.namedtuple('TimeSignature',
                                       ['numerator', 'denominator'])


class QuantizedSequence(object):
  """Holds notes which have been quantized to time steps.

  Notes contain a pitch, velocity, start time, and end time. Notes
  are stored in tracks (which can be different instruments or the same
  instrument). There is also a time signature and key signature.

  Attributes:
    tracks: A dictionary mapping track number to list of Note tuples. Track
        number is taken from the instrument number of each NoteSequence note.
    bpm: Beats per minute. This is needed to recover tempo if converting back
        to MIDI.
    time_signature: This determines the length of a bar of music. This is just
        needed to compute the number of quantization steps per bar, though it
        can also communicate more high level aspects of the music
        (see https://en.wikipedia.org/wiki/Time_signature).
    steps_per_beat: How many quantization steps per beat of music.
  """

  def __init__(self):
    self._reset()

  def _reset(self):
    self.tracks = {}
    self.bpm = 120.0
    self.time_signature = TimeSignature(4, 4)  # numerator, denominator
    self.steps_per_beat = 4

  def from_note_sequence(self, note_sequence, steps_per_beat):
    """Populate self with a music_pb2.NoteSequence proto.

    Notes and time signature are saved to self with notes' start and end times
    quantized. If there is no time signature 4/4 is assumed. If there is more
    than one time signature an exception is raised.

    The beats per minute stored in `note_sequence` is used to normalize tempo.
    Regardless of how fast or slow beats are played, a note that is played
    for 1 beat will last `steps_per_beat` time steps in the quantized result.

    A note's start and end time are snapped to a nearby quantized step. See
    the comments above `QUANTIZE_CUTOFF` for details.
    Args:
      note_sequence: A music_pb2.NoteSequence protocol buffer.
      steps_per_beat: Each beat of music will be divided into this many
          quantized time steps.

    Raises:
      MultipleTimeSignatureException: If there is more than one time signature
          in `note_sequence`.
      BadTimeSignatureException: If the time signature found in `note_sequence`
          has a denominator which is not a power of 2.
      BadNoteException: If a note's quantized start time does not preceed its
          quantized end time.
    """
    self._reset()

    self.steps_per_beat = steps_per_beat

    if len(note_sequence.time_signatures) > 1:
      raise MultipleTimeSignatureException(
          'NoteSequence contains %d time signatures. 0 or 1 expected.' %
          len(note_sequence.time_signatures))
    if note_sequence.time_signatures:
      self.time_signature = TimeSignature(
          note_sequence.time_signatures[0].numerator,
          note_sequence.time_signatures[0].denominator)

    if not is_power_of_2(self.time_signature.denominator):
      raise BadTimeSignatureException(
          'Denominator is not a power of 2. Time signature: %d/%d' %
          (self.time_signature.numerator, self.time_signature.denominator))

    self.bpm = note_sequence.tempos[0].bpm if note_sequence.tempos else 120.0

    # Compute quantization steps per second.
    steps_per_second = steps_per_beat * self.bpm / 60.0

    quantize = lambda x: int(x + (1 - QUANTIZE_CUTOFF))

    for note in note_sequence.notes:
      # Quantize the start and end times of the note.
      start_step = quantize(note.start_time * steps_per_second)
      end_step = quantize(note.end_time * steps_per_second)
      if end_step == start_step:
        end_step += 1

      # Do not allow notes to start or end in negative time.
      if start_step < 0 or end_step < 0:
        raise BadNoteException(
            'Got negative note time: start_step = %s, start_step = %s' %
            (start_step, end_step))

      if note.instrument not in self.tracks:
        self.tracks[note.instrument] = []
      self.tracks[note.instrument].append(Note(pitch=note.pitch,
                                               velocity=note.velocity,
                                               start=start_step,
                                               end=end_step,
                                               instrument=note.instrument,
                                               program=note.program))

  def __eq__(self, other):
    if not isinstance(other, QuantizedSequence):
      return False
    for track in self.tracks:
      if (track not in other.tracks or
          set(self.tracks[track]) != set(other.tracks[track])):
        return False
    return (
        self.bpm == other.bpm and
        self.time_signature == other.time_signature and
        self.steps_per_beat == other.steps_per_beat)
