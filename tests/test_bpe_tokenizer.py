from debug_utils import sentinel
import pytest
from pathlib import Path
from tokenizer.bpe_tokenizer import BPETokenizer


@sentinel
def test_bpe_tokenizer_train_and_encode(tmp_path: Path) -> None:
    # Prepare a small corpus
    corpus = tmp_path / "corpus.txt"
    corpus.write_text("hello world\nhello ai\nworld of ai\n", encoding="utf-8")
    bpe = BPETokenizer(vocab_size=50)
    bpe.train([str(corpus)])
    # Save and reload
    tok_path = tmp_path / "bpe.json"
    bpe.save(tok_path)
    bpe2 = BPETokenizer.load(tok_path)
    # Encode/decode
    ids = bpe2.encode("hello ai")
    text = bpe2.decode(ids)
    assert isinstance(ids, list)
    assert isinstance(text, str)
    assert "hello" in text and "ai" in text
    assert bpe2.vocab_size == len(bpe2.tokenizer.get_vocab())
    assert bpe2.vocab_size != 1000
