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
"""Tests for sequences_lib."""

# internal imports
import tensorflow as tf

from magenta.lib import sequences_lib
from magenta.lib import testing_lib
from magenta.protobuf import music_pb2


class SequencesLibTest(tf.test.TestCase):

  def setUp(self):
    self.steps_per_beat = 4
    self.note_sequence = testing_lib.parse_test_proto(
        music_pb2.NoteSequence,
        """
        time_signatures: {
          numerator: 4
          denominator: 4}
        tempos: {
          bpm: 60}""")
    self.expected_quantized_sequence = sequences_lib.QuantizedSequence()
    self.expected_quantized_sequence.bpm = 60.0
    self.expected_quantized_sequence.steps_per_beat = self.steps_per_beat

  def testEq(self):
    left_hand = sequences_lib.QuantizedSequence()
    left_hand.bpm = 123.0
    left_hand.steps_per_beat = 7
    left_hand.time_signature = sequences_lib.TimeSignature(7, 8)
    testing_lib.add_quantized_track(
        left_hand, 0,
        [(12, 100, 0, 40), (11, 100, 1, 2)])
    testing_lib.add_quantized_track(
        left_hand, 2,
        [(55, 100, 4, 6), (14, 120, 4, 10)])
    testing_lib.add_quantized_track(
        left_hand, 3,
        [(1, 10, 0, 6), (2, 50, 20, 21), (0, 101, 17, 21)])
    right_hand = sequences_lib.QuantizedSequence()
    right_hand.bpm = 123.0
    right_hand.steps_per_beat = 7
    right_hand.time_signature = sequences_lib.TimeSignature(7, 8)
    testing_lib.add_quantized_track(
        right_hand, 0,
        [(11, 100, 1, 2), (12, 100, 0, 40)])
    testing_lib.add_quantized_track(
        right_hand, 2,
        [(14, 120, 4, 10), (55, 100, 4, 6)])
    testing_lib.add_quantized_track(
        right_hand, 3,
        [(0, 101, 17, 21), (2, 50, 20, 21), (1, 10, 0, 6)])
    self.assertEqual(left_hand, right_hand)

  def testFromNoteSequence(self):
    testing_lib.add_track(
        self.note_sequence, 0,
        [(12, 100, 0.01, 10.0), (11, 55, 0.22, 0.50), (40, 45, 2.50, 3.50),
         (55, 120, 4.0, 4.01), (52, 99, 4.75, 5.0)])
    testing_lib.add_quantized_track(
        self.expected_quantized_sequence, 0,
        [(12, 100, 0, 40), (11, 55, 1, 2), (40, 45, 10, 14),
         (55, 120, 16, 17), (52, 99, 19, 20)])
    quantized = sequences_lib.QuantizedSequence()
    quantized.from_note_sequence(self.note_sequence, self.steps_per_beat)
    self.assertEqual(self.expected_quantized_sequence, quantized)

  def testRounding(self):
    testing_lib.add_track(
        self.note_sequence, 1,
        [(12, 100, 0.01, 0.24), (11, 100, 0.22, 0.55), (40, 100, 0.50, 0.75),
         (41, 100, 0.689, 1.18), (44, 100, 1.19, 1.69), (55, 100, 4.0, 4.01)])
    testing_lib.add_quantized_track(
        self.expected_quantized_sequence, 1,
        [(12, 100, 0, 1), (11, 100, 1, 2), (40, 100, 2, 3),
         (41, 100, 3, 5), (44, 100, 5, 7), (55, 100, 16, 17)])
    quantized = sequences_lib.QuantizedSequence()
    quantized.from_note_sequence(self.note_sequence, self.steps_per_beat)
    self.assertEqual(self.expected_quantized_sequence, quantized)

  def testMultiTrack(self):
    testing_lib.add_track(
        self.note_sequence, 0,
        [(12, 100, 1.0, 4.0), (19, 100, 0.95, 3.0)])
    testing_lib.add_track(
        self.note_sequence, 3,
        [(12, 100, 1.0, 4.0), (19, 100, 2.0, 5.0)])
    testing_lib.add_track(
        self.note_sequence, 7,
        [(12, 100, 1.0, 5.0), (19, 100, 2.0, 4.0), (24, 100, 3.0, 3.5)])
    testing_lib.add_quantized_track(
        self.expected_quantized_sequence, 0,
        [(12, 100, 4, 16), (19, 100, 4, 12)])
    testing_lib.add_quantized_track(
        self.expected_quantized_sequence, 3,
        [(12, 100, 4, 16), (19, 100, 8, 20)])
    testing_lib.add_quantized_track(
        self.expected_quantized_sequence, 7,
        [(12, 100, 4, 20), (19, 100, 8, 16), (24, 100, 12, 14)])
    quantized = sequences_lib.QuantizedSequence()
    quantized.from_note_sequence(self.note_sequence, self.steps_per_beat)
    self.assertEqual(self.expected_quantized_sequence, quantized)


if __name__ == '__main__':
  tf.test.main()
