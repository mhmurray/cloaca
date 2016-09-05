define(['jquery'],
function($) {
    /* A wrapper around a selection of cards that handles the
     * minutia of enabling/disabling card selection by setting
     * classes for 'selected' and 'selectable'. 
     */
    function Selectable(selection) {
        // jQuery selection for items to control
        this.$selection = $(selection);
        this.limit = undefined;
    };

    /* Return the keys if it's defined or the whole selection.
     */
    Selectable.prototype.keysOrAll = function(keys) {
        return typeof(keys) === 'undefined' ? this.$selection : keys;
    };

    /* Sets class 'selectable' on keys if keys is defined.
     * Otherwise, operate on the entire selection.
     */
    Selectable.prototype.makeSelectable = function(keys) {
        this.keysOrAll(keys).addClass('selectable');
        return this;
    };

    Selectable.prototype.makeUnselectable = function(keys) {
        this.keysOrAll(keys).removeClass('selectable');
        return this;
    };

    Selectable.prototype.reset = function(keys) {
        this.keysOrAll(keys).removeClass('selectable selected');
        return this;
    };

    Selectable.prototype.selected = function() {
        return this.$selection.filter('.selected');
    };

    Selectable.prototype.unselected = function() {
        return this.$selection.filter('.selectable').not('.selected');
    };

    Selectable.prototype.unselect = function(key) {
        if(!key.hasClass('selected')) {
            console.warn('Tried to unselect non-selected element.');
            return;
        }
        key.removeClass('selected');
        this.addClickCallbacks();
        return this;
    };

    Selectable.prototype.select = function(key) {
        if(key.hasClass('selected')) {
            console.warn('Tried to select already-selected element.');
            return;
        }
        key.addClass('selected');
        this.addClickCallbacks();
        return this;
    };

    Selectable.prototype.addClickCallbacks = function(keys, finishedCallback) {
        var $selection = this.keysOrAll(keys);
        var $unselected = $selection.not('.selected');
        var $selected = $selection.filter('.selected');
        var this_ = this;

        if(typeof(this.limit) === 'undefined' || $selected.length < this.limit) {
            this.makeSelectable($unselected);
            $unselected.off('click.selectable').on('click.selectable', 
                    function(event) {this_.select($(this));}
            );
        } else {
            this.makeUnselectable($unselected.unbind('click'));
            if(typeof(this.finishedCallback) !== 'undefined') {
                this.finishedCallback($selected);
                if(!this.allowBackout) {
                    return this;
                }
            }
        }
        this.makeSelectable($selected);
        $selected.off('click.selectable').on('click.selectable',
                function(event) { this_.unselect($(this)); }
        );
        return this;
    };

    /* Sets up selection with a limit of n cards on specified keys.
     * If keys is not provided, operate on entire selection.
     * The parameter allowBackout will allow selections and unselections
     * to be made even after the limit is reached, activating the callback
     * every time N items are selected.
     */
    Selectable.prototype.makeSelectN = function(n, callback, allowBackout=false) {
        var $selection = this.$selection;
        this.makeSelectable($selection);
        this.limit = n;
        this.finishedCallback = callback;
        this.addClickCallbacks($selection);
        this.allowBackout = allowBackout;
    };

    /* Sets up selection with no limit to how many objects are selected.
     * The callback, if provided, is called when all objects are selected.
     * It will be fired with a jQuery object with all selected keys.
     */
    Selectable.prototype.makeSelectAny = function(callback) {
        var $selection = this.$selection;
        this.makeSelectable($selection);
        this.limit = $selection.length;
        this.finishedCallback = callback;
        this.addClickCallbacks($selection);
    };

    return Selectable;

});
