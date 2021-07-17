<?php

namespace Nominatim\Token;

/**
 * A standard word token.
 */
class Word
{
    /// Database word id, if applicable.
    private $iId;
    /// Number of appearances in the database.
    private $iSearchNameCount;
    /// Number of terms in the word.
    private $iTermCount;

    public function __construct($iId, $iSearchNameCount, $iTermCount)
    {
        $this->iId = $iId;
        $this->iSearchNameCount = $iSearchNameCount;
        $this->iTermCount = $iTermCount;
    }

    public function getId()
    {
        return $this->iId;
    }

    /**
     * Derive new searches by adding this token to an existing search.
     *
     * @param object  $oSearch      Partial search description derived so far.
     * @param object  $oPosition    Description of the token position within
                                    the query.
     *
     * @return SearchDescription[] List of derived search descriptions.
     */
    public function extendSearch($oSearch, $oPosition)
    {
        if ($oPosition->isPhrase('country')) {
            return array();
        }

        // Full words can only be a name if they appear at the beginning
        // of the phrase. In structured search the name must forcably in
        // the first phrase. In unstructured search it may be in a later
        // phrase when the first phrase is a house number.
        if ($oSearch->hasName()
            || !($oPosition->isFirstPhrase() || $oPosition->isPhrase(''))
        ) {
            if ($this->iTermCount > 1
                && ($oPosition->isPhrase('') || !$oPosition->isFirstPhrase())
            ) {
                $oNewSearch = $oSearch->clone(1);
                $oNewSearch->addAddressToken($this->iId);

                return array($oNewSearch);
            }
        } elseif (!$oSearch->hasName(true)) {
            $oNewSearch = $oSearch->clone(1);
            $oNewSearch->addNameToken($this->iId);
            if (CONST_Search_NameOnlySearchFrequencyThreshold
                && $this->iSearchNameCount
                          < CONST_Search_NameOnlySearchFrequencyThreshold
            ) {
                $oNewSearch->markRareName();
            }

            return array($oNewSearch);
        }

        return array();
    }

    public function debugInfo()
    {
        return array(
                'ID' => $this->iId,
                'Type' => 'word',
                'Info' => array(
                           'count' => $this->iSearchNameCount,
                           'terms' => $this->iTermCount
                          )
               );
    }

    public function debugCode()
    {
        return 'W';
    }
}
