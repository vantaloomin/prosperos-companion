from companion.memory.chunks import compile_chunks
from companion.memory.hybrid_recall import hybrid_hits
from companion.memory.retrieval import STOP, Corpus


def chunks(*texts):
    return [chunk for index, text in enumerate(texts) for chunk in compile_chunks(f's{index}', 'note', text)]


def test_conversation_words_are_searchable():
    assert 'story' not in STOP and 'continue' not in STOP
    hits = Corpus(chunks('Tell me a story about the lighthouse', 'Groceries: milk and eggs')).search('story')
    assert [hit.chunk.source_id for hit in hits] == ['s0']


def test_hybrid_fusion_accepts_caller_rankings():
    sources = chunks('Genmaicha is my favourite tea', 'The interview is on Thursday')
    semantic = {'rankings': [[sources[1].id, 'unknown-id']]}
    hits = hybrid_hits(sources, ['tea'], semantic, limit=5)
    assert {hit.chunk.id for hit in hits} == {sources[0].id, sources[1].id}
