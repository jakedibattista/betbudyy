# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Tests for t_content."""

import pytest
import pydantic

from ... import _transformers as t
from ... import types

def test_none():
  with pytest.raises(ValueError) as e:
    t.t_content(None, None)
  assert 'content is required' in str(e)


def test_content_no_role():
  content = t.t_content(
      None, types.Content(parts=[types.Part(text='hello world')])
  )
  
  assert content == types.Content(parts=[types.Part(text='hello world')])
  assert not content.role


def test_content_with_role():
  assert t.t_content(
      None,
      types.Content(
          role='user', parts=[types.Part(text='hello world')]
      ),
  ) == types.Content(role='user', parts=[types.Part(text='hello world')])


def test_part():
  content = t.t_content(None, types.Part(text='hello world'))

  assert content == types.UserContent(
      parts=[types.Part(text='hello world')]
  )
  assert content.role == 'user'



def test_string():
  content = t.t_content(None, 'hello world')

  assert content == types.UserContent(
      parts=[types.Part(text='hello world')]
  )
  assert content.role == 'user'


def test_file():
  content = t.t_content(
      None,
      types.File(
          name='file.txt', mime_type='text/plain', uri='gs://bucket/file.txt'
      ),
  )
  assert content == types.UserContent(
      parts=[
          types.Part(
              file_data=types.FileData(
                  mime_type='text/plain',
                  file_uri='gs://bucket/file.txt',
              )
          ),
      ]
  )
  assert content.role == 'user'


def test_content_dict_with_role():
  assert t.t_content(
      None,
      {
          'role': 'model',
          'parts': [
              {
                  'text': 'hello world',
              },
          ],
      },
  ) == types.Content(
      role='model',
      parts=[types.Part(text='hello world')],
  )


def test_content_dict_without_role():
  content = t.t_content(
      None,
      {
          'parts': [
              {
                  'text': 'hello world',
              },
          ],
      },
  )
  assert content == types.Content(
      parts=[types.Part(text='hello world')]
  )
  assert not content.role


def test_part_dict():
  content = t.t_content(None, {'text': 'hello world'})

  assert content == types.UserContent(
      parts=[types.Part(text='hello world')]
  )
  assert content.role == 'user'



