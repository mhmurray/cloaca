define(['jquery'],
function($) {
    /* A wrapper around a selection of cards that handles the
     * minutia of enabling/disabling card selection by setting
     * classes for 'selected' and 'selectable'. 
     */
    function Zone(selection) {
        // jQuery selection for this zone
        this.$selection = $(selection);
        this.limit = undefined;
    };

    /* Return the keys if it's defined or the whole selection.
     */
    Zone.prototype.keysOrAll = function(keys) {
        return typeof(keys) === 'undefined' ? this.$selection : keys;
    };

    /* Sets class 'selectable' on keys if keys is defined.
     * Otherwise, operate on the entire selection.
     */
    Zone.prototype.makeSelectable = function(keys) {
        this.keysOrAll(keys).addClass('selectable');
        return this;
    };

    Zone.prototype.makeUnselectable = function(keys) {
        this.keysOrAll(keys).removeClass('selectable');
        return this;
    };

    Zone.prototype.reset = function(keys) {
        this.keysOrAll(keys).removeClass('selectable selected');
        return this;
    };

    Zone.prototype.selected = function() {
        return this.$selection.filter('.selected');
    };

    Zone.prototype.unselected = function() {
        return this.$selection.filter('.selectable').not('.selected');
    };

    Zone.prototype.unselect = function(key) {
        if(!key.hasClass('selected')) {
            console.warn('Tried to unselect non-selected element.');
            return;
        }
        console.log(key[0].id + ' unselected!.');
        key.removeClass('selected');
        this.addClickCallbacks();
        return this;
    };

    Zone.prototype.select = function(key) {
        if(key.hasClass('selected')) {
            console.warn('Tried to select already-selected element.');
            return;
        }
        console.log(key[0].id + ' selected!.');
        key.addClass('selected');
        this.addClickCallbacks();
        return this;
    };

    Zone.prototype.addClickCallbacks = function(keys) {
        var $selection = this.keysOrAll(keys);
        var $unselected = $selection.not('.selected');
        var $selected = $selection.filter('.selected');
        var this_ = this;

        if(typeof(this.limit) === 'undefined' || $selected.length < this.limit) {
            this.makeSelectable($unselected);
            $unselected.unbind('click').click(function(event) {
                var $target = $(event.target);
                this_.select($target);
            });
        } else {
            this.makeUnselectable($unselected.unbind('click'));
        }
        this.makeSelectable($selected);
        $selected.unbind('click').click(function(event) {
            var $target = $(event.target);
            this_.unselect($target);
        });
        return this;
    };

    /* Sets up selection with a limit of n cards on specified keys.
     * If keys is not provided, operate on entire selection.
     */
    Zone.prototype.makeSelectN = function(n) {
        var $selection = this.$selection;
        this.makeSelectable($selection);
        this.limit = n;
        this.addClickCallbacks($selection);
    };

    return Zone;

});
