/**
 * @author oaxmcgi
 */
function init() {
    google.earth.createInstance('map3d', initCB, failureCB);
 }
 function initCB(instance) {
            ge = instance;
            ge.getWindow().setVisibility(true);
            ge.getNavigationControl().setVisibility(ge.VISIBILITY_SHOW);
            var href = location.protocol + '//' + location.hostname +  '/github/250CrossingPhiladelphia/lib/tracks/Akh-Total.kml';
            google.earth.fetchKml(ge, href, fetchCallback);
        }
function fetchCallback(fetchedKml) {
   // Alert if no KML was found at the specified URL.
   if (!fetchedKml) {
      setTimeout(function() {
         alert('Bad or null KML');
      }, 0);
      return;
   }

   // Add the fetched KML into this Earth instance.
   ge.getFeatures().appendChild(fetchedKml);

   // Walk through the KML to find the tour object; assign to variable 'tour.'
   walkKmlDom(fetchedKml, function() {
      if (this.getType() === 'KmlTour') {
         tour = this;
         return false;
      }
   });
   enterTour();
}
function enterTour() {
    if (!tour) {
       alert('No tour found!');
       return;
    }
    ge.getTourPlayer().setTour(tour);
    setTimeout(function(){
        ge.getTourPlayer().play();
        }, 500);
 };
 function failureCB(errorCode) {
    //TODO: Better Error Handling 
}
