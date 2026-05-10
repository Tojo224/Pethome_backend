import unicodedata
from difflib import SequenceMatcher


class TextMatcher:
    @staticmethod
    def normalize(text):
        if text is None:
            return ""

        text = str(text).strip().lower()

        text = "".join(
            char
            for char in unicodedata.normalize("NFD", text)
            if unicodedata.category(char) != "Mn"
        )

        return text

    @staticmethod
    def similarity(a, b):
        a_norm = TextMatcher.normalize(a)
        b_norm = TextMatcher.normalize(b)

        if not a_norm or not b_norm:
            return 0

        return SequenceMatcher(None, a_norm, b_norm).ratio()

    @staticmethod
    def contains_match(search_text, candidate_text):
        search_norm = TextMatcher.normalize(search_text)
        candidate_norm = TextMatcher.normalize(candidate_text)

        if not search_norm or not candidate_norm:
            return False

        return search_norm in candidate_norm or candidate_norm in search_norm

    @staticmethod
    def find_best_matches(search_text, candidates, label_getter, min_score=0.45):
        """
        Busca coincidencias aproximadas.

        candidates:
            Lista de objetos o diccionarios.

        label_getter:
            FunciAn que recibe un candidato y devuelve el texto comparable.
        """

        matches = []

        for candidate in candidates:
            label = label_getter(candidate)

            contains = TextMatcher.contains_match(search_text, label)
            score = TextMatcher.similarity(search_text, label)

            if contains:
                score = max(score, 0.9)

            if score >= min_score:
                matches.append(
                    {
                        "item": candidate,
                        "label": label,
                        "score": score,
                    }
                )

        matches.sort(key=lambda x: x["score"], reverse=True)

        return matches