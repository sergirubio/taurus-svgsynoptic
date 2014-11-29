from taurus import Attribute, Manager
from taurus.core.taurusbasetypes import AttrQuality, TaurusEventType, DataFormat
import PyTango

Manager().changeDefaultPollingPeriod(1000)


def error_str(err):
    if isinstance(err, PyTango.DevFailed):
        err = err[0]
        return "[{0}] {1}".format(err.reason, err.desc)
    return str(err)


# Based on code from the taurus-web project
class TaurusWebAttribute(object):
    """This object is a listener for the taurus attribute value.
    When a attribute changes it sends an event. The event
    triggers a call to *eventReceived*. *eventReceived* will transform
    the change event into a JSON encoded string and sends this
    string through the web socket to the client"""

    def __init__(self, name, callback):
        print self.__class__.__name__, name
        self.name = name
        self.callback = callback
        self._last_time = 0
        self.last_value_event = None
        self.last_config_event = None
        self.attribute.addListener(self)

    @property
    def attribute(self):
        return Attribute(self.name)

    def eventReceived(self, evt_src, evt_type, evt_value):
        self.callback(evt_src, evt_type, evt_value)

    def _eventReceived(self, evt_src, evt_type, evt_value):
        """Transforms the event into a JSON encoded string and sends this
        string into the web socket"""

        modelObj = evt_src
        data = {}
        if evt_type == TaurusEventType.Error:
            data["event_type"] = "error"
            data["error"] = error_str(evt_value)
        else:
            if evt_type == TaurusEventType.Config:
                modelObj = evt_src.getParentObj()
                data['event_type'] = "config"
                data['description'] = evt_src.description
                data['label'] = evt_src.label
                data["unit"] = evt_src.unit if evt_src.unit != "No unit" else ""
                data["format"] = evt_src.format
                self.last_config_event = data
            else:   #if evt_value.time.tv_sec > self._last_time + 0.1:  # debounce
                self._last_time = evt_value.time.tv_sec
                data["event_type"] = "value"
                value = evt_value.value
                quality = evt_value.quality
                fmt = evt_value.data_format
                if fmt == DataFormat._0D:
                    html = modelObj.displayValue(value)
                    if isinstance(value, PyTango._PyTango.DevState):
                        # html = '<span class="state-%s">%s</span>' % (
                        #     value.name, value.name
                        # )
                        value = value.name
                    if isinstance(value, str):
                        html = value.replace("\n", "<br>")
                elif fmt in (DataFormat._1D, DataFormat._2D):
                    # bad, very bad performance! Don't worry for now
                    value = value.tolist()
                    html = "[...]"
                data['value'] = value
                data['html'] = html
                data['quality'] = str(quality)
                data['time'] = evt_value.time.tv_sec
                data['type'] = str(evt_value.type)  # can this change..?
                self.last_value_event = data
                #data['format'] = modelObj.format if modelObj.format != "Not specified" else ""

        data['model'] = modelObj.getNormalName()
        #print("eventReceived", data["model"], str(evt_type))
        # try:
        #     #json_data = json.dumps({"event": data})
        # except TypeError as te:
        #     #data['css'] = {'color':'white', 'background-color' : 'violet'}
        #     data['html'] = data['value'] = str(te)
        #     json_data = jsondumps({"event": data})
        #print(json_data)

        self.write_message(data)

    def write_message(self, message):
        self.callback(message)

    def clear(self):
        self.attribute.removeListener(self)
