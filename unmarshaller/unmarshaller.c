/* -*- Mode: C; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 4 -*- */

/*
 * unmarshaller.c
 *
 * Copyright (C) 2002 Ximian, Inc.
 *
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License as
 * published by the Free Software Foundation; either version 2 of the
 * License, or (at your option) any later version.
 * 
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 * 
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
 * USA.
 */

#include <Python.h>
#include <glib.h>
#include <glib-object.h>
#include <expat.h>


#define G_TYPE_BASE64 base64_get_type()

static gchar *
base64_copy (const gchar *buf)
{
    return g_strdup (buf);
}

static void
base64_free (gchar *buf)
{
    g_free (buf);
}

static GType
base64_get_type (void)
{
    static GType type = 0;

    if (type == 0)
        type = g_boxed_type_register_static ("Base64",
                                             (GBoxedCopyFunc) base64_copy,
                                             (GBoxedFreeFunc) base64_free);

    return type;
}



typedef struct {
	GValue      *parent;
	GValueArray *array;
} Node;

static Node *node_copy (const Node *node);
static void  node_free (Node *node);

#define G_TYPE_LIST list_get_type()
#define G_TYPE_DICT dict_get_type()

static GType
list_get_type (void)
{
    static GType type = 0;

    if (type == 0)
        type = g_boxed_type_register_static ("List",
                                             (GBoxedCopyFunc) node_copy,
                                             (GBoxedFreeFunc) node_free);

    return type;
}

static GType
dict_get_type (void)
{
    static GType type = 0;

    if (type == 0)
        type = g_boxed_type_register_static ("Dict",
                                             (GBoxedCopyFunc) node_copy,
                                             (GBoxedFreeFunc) node_free);

    return type;
}

static GValue *
node_new (GType type, GValue *parent, GValueArray *array)
{
	GValue *self;
	Node   *node;

	self = g_new0 (GValue, 1);
	self = g_value_init (self, type);

	node = g_new (Node, 1);
	node->parent = parent;
	node->array = array;

    g_value_set_boxed (self, (gpointer) node);
    node_free (node);

	return self;
}

#define list_new(parent, array) node_new(G_TYPE_LIST, parent, array)
#define dict_new(parent, array) node_new(G_TYPE_DICT, parent, array)

static Node *
node_copy (const Node *node)
{
	Node *dest;

	dest = g_new (Node, 1);
    dest->parent = node->parent;
    dest->array = g_value_array_copy (node->array);

    return dest;
}

static void
node_free (Node *node)
{
	g_value_array_free (node->array);
	g_free (node);
}

static void
node_push (GValue *self, GValue *child)
{
	Node *node;

	node = (Node *) g_value_get_boxed (self);
	node->array = g_value_array_append (node->array,
                                        child);
    g_value_unset (child);
    g_free (child);
}

static GValue *
node_pop (GValue *self)
{
    Node *node;

	node = (Node *) g_value_get_boxed (self);

    if (node->parent)
        return node->parent;

    g_warning ("Trying to pop root node");
    return self;
}

static guint
node_children_count (GValue *self)
{
    Node *node;

	node = (Node *) g_value_get_boxed (self);

    return node->array->n_values;
}

static GValue *
node_children_nth (GValue *self, guint n)
{
    Node *node;

	node = (Node *) g_value_get_boxed (self);

    return g_value_array_get_nth (node->array, n);
}

#define node_children_last(self) node_children_nth (self, node_children_count (unm->cursor) - 1);

enum PyUnmarshallerFlavor {
    PY_UNMARSHALLER_FLAVOR_NONE,
    PY_UNMARSHALLER_FLAVOR_PARAMS,
    PY_UNMARSHALLER_FLAVOR_FAULT,
    PY_UNMARSHALLER_FLAVOR_METHODNAME
};

typedef struct _PyUnmarshaller PyUnmarshaller;
struct _PyUnmarshaller {
    PyObject_HEAD;
	XML_Parser parser;
    enum PyUnmarshallerFlavor flavor;
    GValue    *stack;
    GValue    *cursor;
    GString   *data;
    char      *methodname;
    char      *encoding;
    int        value;
    PyObject  *binary_cb;
    PyObject  *boolean_cb;
    PyObject  *fault_cb;
};

static void      unmarshaller_dealloc (PyObject *);
static PyObject *unmarshaller_getattr (PyUnmarshaller *, char *);
static PyObject *unmarshaller_new     (PyObject *, PyObject *);

static PyTypeObject PyUnmarshallerType = {
    PyObject_HEAD_INIT (NULL)
    0,
    "ximian_unmarshaller",
    sizeof (PyUnmarshaller),
    0,
    unmarshaller_dealloc,
    0, /* tp_print */  
    (getattrfunc) unmarshaller_getattr,
    0, /*tp_setattr*/
    0, /*tp_compare*/
    0, /*tp_repr*/
    0, /*tp_as_number*/
    0, /*tp_as_sequence*/
    0, /*tp_as_mapping*/
    0, /*tp_hash */
};

static PyMethodDef general_methods[] = {
    { "new", unmarshaller_new, METH_VARARGS, "Create a new unmarshaller" },
    { NULL, NULL, 0, NULL }
};

static PyObject *
g_value_boolean_to_PyObject (GValue *val, PyObject *boolean_cb)
{
    PyObject *obj;
    PyObject *args;
    gboolean bool;

    bool = g_value_get_boolean (val);

    if (boolean_cb) {
        args = Py_BuildValue ("(i)", bool);
        obj = PyEval_CallObject (boolean_cb, args);
        Py_DECREF (args);
    }

    if (!obj) {
        g_warning("Couldn't build PyObject for boolean %d\n", bool);
        Py_INCREF(Py_None);
        obj = Py_None;
    }

    return obj;
}

static PyObject *
g_value_base64_to_PyObject (GValue *val, PyObject *base64_cb)
{
    PyObject *obj;
    PyObject *args;
    char *data;

    data = (char *) g_value_get_boxed (val);

    if (base64_cb) {
        args = Py_BuildValue ("(s)", data);
        obj = PyEval_CallObject (base64_cb, args);
        Py_DECREF (args);
    }

    if (!obj) {
        g_warning("Couldn't build PyObject for base64\n");
        Py_INCREF(Py_None);
        obj = Py_None;
    }

    return obj;
}

static PyObject *
g_value_to_PyObject (GValue *val, PyObject *boolean_cb, PyObject *base64_cb)
{
    GType type;
    PyObject *obj;
    int len, i;

    type = G_VALUE_TYPE(val);
    switch (type) {
    case G_TYPE_BOOLEAN:
        obj = g_value_boolean_to_PyObject(val, boolean_cb);
        break;
    case G_TYPE_INT:
        obj = Py_BuildValue ("i", g_value_get_int (val));
        break;
    case G_TYPE_DOUBLE:
        obj = Py_BuildValue ("d", g_value_get_double (val));
        break;
    case G_TYPE_STRING:
        obj = Py_BuildValue ("s", g_value_get_string (val));
        break;

    default:
        if (type == G_TYPE_LIST) {
            len = node_children_count (val);
            obj = PyList_New (len);
            for (i = 0; i < len; i++) {
                GValue *v = node_children_nth (val, i);
                PyList_SetItem (obj, i, g_value_to_PyObject (v, boolean_cb, base64_cb));
            }
        } else if (type == G_TYPE_DICT) {
            obj = PyDict_New ();
            len = node_children_count (val);
            for (i = 0; i < len; i++) {
                GValue *key = node_children_nth (val, i);
                GValue *v = node_children_nth (val, ++i);

                PyObject *py_key = g_value_to_PyObject (key, boolean_cb, base64_cb);
                PyObject *py_val = g_value_to_PyObject (v, boolean_cb, base64_cb);

                PyDict_SetItem (obj, py_key, py_val);
                Py_XDECREF (py_key);
                Py_XDECREF (py_val);
            }
        } else if (type == G_TYPE_BASE64) {
            obj = g_value_base64_to_PyObject(val, base64_cb);
            break;
        } else {
            g_warning ("Unhandled GType");
            Py_INCREF (Py_None);
            obj = Py_None;
        }
    }

    return obj;
}

static PyObject *
unmarshaller_close (PyObject *self, PyObject *args)
{
    PyUnmarshaller *unm = (PyUnmarshaller *) self;
    PyObject *tuple, *result, *obj;
    int len, i;

    if (unm->flavor == PY_UNMARSHALLER_FLAVOR_FAULT
        && unm->fault_cb
        && node_children_count (unm->stack) > 0) {

        args = Py_BuildValue ("(O)",
                              g_value_to_PyObject (node_children_nth (unm->stack, 0),
                                                   unm->boolean_cb, unm->binary_cb));
        result = PyEval_CallObject (unm->fault_cb, args);
        Py_DECREF (args);
        if (result == NULL) /* throw exception */
            return NULL;
        Py_DECREF (result);
    }

    /* tuple-ify the stack */
    len = node_children_count (unm->stack);
    tuple = PyTuple_New (len);

    for (i = 0; i < len; i++) {
        obj = g_value_to_PyObject (node_children_nth (unm->stack, i),
                                   unm->boolean_cb, unm->binary_cb);
        PyTuple_SetItem (tuple, i, obj);
    }

    return tuple;
}

static PyObject *
unmarshaller_getmethodname (PyObject *self, PyObject *args)
{
    PyUnmarshaller *unm = (PyUnmarshaller *) self;

    if (unm->methodname) 
        return Py_BuildValue ("s", unm->methodname);

    Py_INCREF (Py_None);
    return Py_None;
}

static PyObject *
unmarshaller_feed (PyObject *self, PyObject *args)
{
	PyUnmarshaller *unm = (PyUnmarshaller *) self;
	char *data_str;
	int done;

	if (! PyArg_ParseTuple (args, "si", &data_str, &done))
		return NULL;

    Py_BEGIN_ALLOW_THREADS
	XML_Parse (unm->parser, data_str, strlen(data_str), done);
    Py_END_ALLOW_THREADS

	Py_INCREF (Py_None);
	return Py_None;
}

static void
start_element_cb (gpointer self, const char *name, const char **atts)
{
    PyUnmarshaller *unm = (PyUnmarshaller *) self;

    if (!strcmp (name, "array")) {
        node_push (unm->cursor,
                   list_new (unm->cursor, g_value_array_new (0)));
        unm->cursor = node_children_last (unm->cursor);
    }

    if (!strcmp (name, "struct")) {
        node_push (unm->cursor,
                   dict_new (unm->cursor,
                             g_value_array_new (0)));
        unm->cursor = node_children_last (unm->cursor);
    }

    g_string_assign (unm->data, "");

    unm->value = !strcmp (name, "value");
}

static void
char_data_cb (gpointer self, const char *data, int len)
{
    PyUnmarshaller *unm = (PyUnmarshaller *) self;

    g_string_append_len (unm->data, data, len);
}

/* ** ** ** ** ** ** ** ** ** ** ** ** ** ** ** ** ** ** ** ** ** ** ** ** */

static void
end_boolean (PyUnmarshaller *unm, const char *data)
{
    GValue *val;

    val = g_new0 (GValue, 1);
    val = g_value_init (val, G_TYPE_BOOLEAN);
    g_value_set_boolean (val, atoi (data));

    node_push (unm->cursor, val);
    unm->value = 0;
}

static void
end_int (PyUnmarshaller *unm, const char *data)
{
    GValue *val;

    val = g_new0 (GValue, 1);
    val = g_value_init (val, G_TYPE_INT);
    g_value_set_int (val, atoi (data));

    node_push (unm->cursor, val);
    unm->value = 0;
}

static void
end_double (PyUnmarshaller *unm, const char *data)
{
    GValue *val;

    val = g_new0 (GValue, 1);
    val = g_value_init (val, G_TYPE_DOUBLE);
    g_value_set_double (val, atof (data));

    node_push (unm->cursor, val);
    unm->value = 0;
}

static void
end_string (PyUnmarshaller *unm, const char *data)
{
    GValue *val;

    /* FIXME: ignores all issues regarding the encoding of the data */
    val = g_new0 (GValue, 1);
    val = g_value_init (val, G_TYPE_STRING);
    g_value_set_string (val, data);

    node_push (unm->cursor, val);
    unm->value = 0;
}

static void
end_array (PyUnmarshaller *unm, const char *data)
{
    g_assert (G_VALUE_TYPE(unm->cursor) == G_TYPE_LIST);

    unm->cursor = node_pop (unm->cursor);
    unm->value = 0;
}

static void
end_struct (PyUnmarshaller *unm, const char *data)
{
    g_assert (G_VALUE_TYPE(unm->cursor) == G_TYPE_DICT);

    unm->cursor = node_pop (unm->cursor);
    unm->value = 0;
}

static void
end_base64 (PyUnmarshaller *unm, const char *data)
{
    GValue *val;

    /* FIXME: ignores all issues regarding the encoding of the data */
    val = g_new0 (GValue, 1);
    val = g_value_init (val, G_TYPE_BASE64);
    g_value_set_boxed (val, data);

    node_push (unm->cursor, val);
    unm->value = 0;

#if 0
    PyObject *binary;
    PyObject *args;
    GValue *val;
    char *data_str;

    args = Py_BuildValue ("(s)", data);
    binary = PyEval_CallObject (unm->binary_cb, args);
    Py_DECREF (args);

    if (binary == NULL)
        return;

    if (!PyArg_ParseTuple (binary, "i", &data_str))
        return;

    Py_DECREF(binary);

    end_string (unm, data_str);

    unm->value = 0;
#endif
}

#if 0
static void
end_dateTime (PyUnmarshaller *unm, const char *data)
{
    g_assert_not_reached ();
}
#endif

static void
end_value (PyUnmarshaller *unm, const char *data)
{
    if (unm->value)
        end_string (unm, data);
}

static void
end_params (PyUnmarshaller *unm, const char *data)
{
    unm->flavor = PY_UNMARSHALLER_FLAVOR_PARAMS;
}

static void
end_fault (PyUnmarshaller *unm, const char *data)
{
    unm->flavor = PY_UNMARSHALLER_FLAVOR_FAULT;
}

#if 0
static void
end_methodName (PyUnmarshaller *unm, const char *data)
{
    g_free (unm->methodname);
    unm->methodname = g_strdup (data);
    unm->flavor = PY_UNMARSHALLER_FLAVOR_METHODNAME;
}
#endif

static void
end_element_cb (gpointer self, const char *name)
{
    PyUnmarshaller *unm = (PyUnmarshaller *) self;
    char *data_str;
    void (*fn) (PyUnmarshaller *, const char *str) = NULL;

    data_str = unm->data->str;

    switch (*name) {

    case 'a':
        if (! strcmp (name, "array"))
            fn = end_array;
        break;

    case 'b':
        if (! strcmp (name, "boolean"))
            fn = end_boolean;
        else if (! strcmp (name, "base64"))
            fn = end_base64;
        break;

    case 'd':
        if (! strcmp (name, "double"))
            fn = end_double;
        break;

    case 'f':
        if (! strcmp (name, "fault"))
            fn = end_fault;
        break;

    case 'i':
        if (! strcmp (name, "i4") || ! strcmp (name, "int"))
            fn = end_int;
        break;

    case 'n':
        if (! strcmp (name, "name"))
            fn = end_string;
        break;

    case 'p':
        if (! strcmp (name, "params"))
            fn = end_params;
        break;

    case 's':
        if (! strcmp (name, "string"))
            fn = end_string;
        else if (! strcmp (name, "struct"))
            fn = end_struct;
        break;

    case 'v':
        if (! strcmp (name, "value"))
            fn = end_value;
        break;
    }

    if (fn)
        fn (unm, data_str);
}

/* ** ** ** ** ** ** ** ** ** ** ** ** ** ** ** ** ** ** ** ** ** ** ** ** */

static PyObject *
unmarshaller_new (PyObject *self, PyObject *args)
{
    PyUnmarshaller *unm;
    PyObject *binary_cb, *boolean_cb, *fault_cb;

    if (!PyArg_ParseTuple (args, "OOO:new_unmarshaller",
                           &binary_cb, &boolean_cb, &fault_cb))
        return NULL;
    
#if PY_MAJOR_VERSION == 2
    unm = PyObject_New (PyUnmarshaller, &PyUnmarshallerType);
#else
    unm = PyObject_NEW (PyUnmarshaller, &PyUnmarshallerType);
#endif

    unm->parser = XML_ParserCreate (NULL);
    XML_SetUserData (unm->parser, unm);
    XML_SetElementHandler (unm->parser, start_element_cb, end_element_cb);
    XML_SetCharacterDataHandler (unm->parser, char_data_cb);

    unm->flavor = PY_UNMARSHALLER_FLAVOR_NONE;
    unm->stack = list_new (NULL, g_value_array_new (0));
    unm->cursor = unm->stack;
    unm->data = g_string_new ("");
    unm->methodname = NULL;
    unm->encoding = g_strdup ("utf-8");
    unm->binary_cb = binary_cb;
    unm->boolean_cb = boolean_cb;
    unm->fault_cb = fault_cb;

    Py_INCREF (unm->binary_cb);
    Py_INCREF (unm->boolean_cb);
    Py_INCREF (unm->fault_cb);

    return (PyObject *) unm;
}

static void
unmarshaller_dealloc (PyObject *self)
{
    PyUnmarshaller *unm = (PyUnmarshaller *) self;

    XML_ParserFree (unm->parser);

    g_value_unset (unm->stack);
    g_free (unm->stack);

    g_string_free (unm->data, TRUE);
    g_free (unm->methodname);
    g_free (unm->encoding);

#if PY_MAJOR_VERSION == 2
    PyObject_Del (self);
#else
    PyMem_DEL (self);
#endif
}

static PyMethodDef unmarshaller_methods[] = {
    { "close", unmarshaller_close, METH_VARARGS, "close" },
    { "getmethodname", unmarshaller_getmethodname, METH_VARARGS, "getmethodname" },
    { "feed",   unmarshaller_feed,   METH_VARARGS, "feed" },
    { NULL, NULL, 0, NULL }
};

static PyObject *
unmarshaller_getattr (PyUnmarshaller *unm, char *name)
{
    return Py_FindMethod (unmarshaller_methods, (PyObject *) unm, name);
}

DL_EXPORT (void)
initximian_unmarshaller (void)
{
    PyUnmarshallerType.ob_type = &PyType_Type;

    Py_InitModule("ximian_unmarshaller",
                  general_methods);

    g_type_init ();
}
