/* -*- Mode: C; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 4 -*- */

/*
 * unmarshaller.c
 *
 * Copyright (C) 2002 Ximian, Inc.
 *
 */

/*
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

#include <glib.h>
#include <Python.h>

enum PyUnmarshallerFlavor {
    PY_UNMARSHALLER_FLAVOR_NONE,
    PY_UNMARSHALLER_FLAVOR_PARAMS,
    PY_UNMARSHALLER_FLAVOR_FAULT,
    PY_UNMARSHALLER_FLAVOR_METHODNAME
};

typedef struct _PyUnmarshaller PyUnmarshaller;
struct _PyUnmarshaller {
    PyObject_HEAD;
    enum PyUnmarshallerFlavor flavor;
    GPtrArray *stack;
    GSList    *marks;
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
unmarshaller_close (PyObject *self, PyObject *args)
{
    PyUnmarshaller *unm = (PyUnmarshaller *) self;
    PyObject *tuple;
    int i;

    if (unm->flavor == PY_UNMARSHALLER_FLAVOR_FAULT
        && unm->fault_cb
        && unm->stack->len > 0) {
        args = Py_BuildValue ("(O)", g_ptr_array_index (unm->stack, 0));
        PyEval_CallObject (unm->fault_cb, args);
    }

    /* tuple-ify the stack */
    tuple = PyTuple_New (unm->stack->len);
    for (i = 0; i < unm->stack->len; ++i) {
        PyObject *obj = g_ptr_array_index (unm->stack, i);
        PyTuple_SetItem (tuple, i, obj);
        Py_INCREF (obj);
        ++i;
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
unmarshaller_xml (PyObject *self, PyObject *args)
{
#if 0
    PyUnmarshaller *unm = (PyUnmarshaller *) self;
    char *encoding;
    int standalone;

    /* FIXME: do nothing for now */

    if (! PyArg_ParseTuple (args, "si", &encoding, &standalone))
        return NULL;

    g_free (unm->encoding);
    unm->encoding = g_strdup (encoding);

    g_assert (standalone);
#endif

    Py_INCREF (Py_None);
    return Py_None;
}

static PyObject *
unmarshaller_start (PyObject *self, PyObject *args)
{
    PyUnmarshaller *unm = (PyUnmarshaller *) self;
    PyObject *dummy;
    char *tag;

    if (! PyArg_ParseTuple (args, "sO", &tag, &dummy))
        return NULL;

    if (!strcmp (tag, "array") || !strcmp (tag, "struct"))
        unm->marks =
            g_slist_prepend (unm->marks,
                             GINT_TO_POINTER (unm->stack->len));

    g_string_assign (unm->data, "");

    unm->value = !strcmp (tag, "value");

    Py_INCREF (Py_None);
    return Py_None;
}

static PyObject *
unmarshaller_data (PyObject *self, PyObject *args)
{
    PyUnmarshaller *unm = (PyUnmarshaller *) self;
    char *data_str;

    if (! PyArg_ParseTuple (args, "s", &data_str))
        return NULL;
    
    g_string_append (unm->data, data_str);

    Py_INCREF (Py_None);
    return Py_None;
}

/* ** ** ** ** ** ** ** ** ** ** ** ** ** ** ** ** ** ** ** ** ** ** ** ** */

static void
end_boolean (PyUnmarshaller *unm, const char *data)
{
    PyObject *args;
    PyObject *bool;

    args = Py_BuildValue ("(s)", data);
    bool = PyEval_CallObject (unm->boolean_cb, args);
    Py_DECREF (args);

    g_ptr_array_add (unm->stack, bool);

    unm->value = 0;
}

static void
end_int (PyUnmarshaller *unm, const char *data)
{
    PyObject *obj = Py_BuildValue ("i", atoi (data));
    g_ptr_array_add (unm->stack, obj);
    unm->value = 0;
}

static void
end_double (PyUnmarshaller *unm, const char *data)
{
    PyObject *obj = Py_BuildValue ("d", atof (data));
    g_ptr_array_add (unm->stack, obj);
    unm->value = 0;
}

static void
end_string (PyUnmarshaller *unm, const char *data)
{
    /* FIXME: ignores all issues regarding the encoding of the data */
    PyObject *obj = Py_BuildValue ("s", data);
    g_ptr_array_add (unm->stack, obj);
    unm->value = 0;
}

static void
end_array (PyUnmarshaller *unm, const char *data)
{
    PyObject *list;
    int mark, i;
    
    g_assert (unm->marks);
    mark = GPOINTER_TO_INT (unm->marks->data);
    
    unm->marks = g_slist_delete_link (unm->marks,
                                      unm->marks);

    list = PyList_New (unm->stack->len - mark);

    for (i = mark; i < unm->stack->len; ++i) {
        PyObject *obj = g_ptr_array_index (unm->stack, i);
        PyList_SetItem (list, i - mark, obj);
    }

    g_ptr_array_set_size (unm->stack, mark);
    g_ptr_array_add (unm->stack, list);
    
    unm->value = 0;
}

static void
end_struct (PyUnmarshaller *unm, const char *data)
{
    PyObject *dict;
    int mark, i;

    g_assert (unm->marks);
    mark = GPOINTER_TO_INT (unm->marks->data);
    
    unm->marks = g_slist_delete_link (unm->marks,
                                      unm->marks);

    dict = PyDict_New ();

    for (i = mark; i < unm->stack->len; i += 2) {
        PyObject *key = g_ptr_array_index (unm->stack, i);
        PyObject *value = g_ptr_array_index (unm->stack, i+1);

        PyDict_SetItem (dict, key, value);
    }

    g_ptr_array_set_size (unm->stack, mark);
    g_ptr_array_add (unm->stack, dict);
    
    unm->value = 0;
}

static void
end_base64 (PyUnmarshaller *unm, const char *data)
{
    PyObject *binary;
    PyObject *args;

    args = Py_BuildValue ("(s)", data);
    binary = PyEval_CallObject (unm->binary_cb, args);
    Py_DECREF (args);

    g_ptr_array_add (unm->stack, binary);

    unm->value = 0;
}

static void
end_dateTime (PyUnmarshaller *unm, const char *data)
{
    g_assert_not_reached ();
}

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

static void
end_methodName (PyUnmarshaller *unm, const char *data)
{
    g_free (unm->methodname);
    unm->methodname = g_strdup (data);
    unm->flavor = PY_UNMARSHALLER_FLAVOR_METHODNAME;
}

static PyObject *
unmarshaller_end (PyObject *self, PyObject *args)
{
    PyUnmarshaller *unm = (PyUnmarshaller *) self;
    char *tag;
    char *data_str = NULL;
    void (*fn) (PyUnmarshaller *, const char *str) = NULL;

    if (! PyArg_ParseTuple (args, "s", &tag))
        return NULL;

    data_str = unm->data->str;

    switch (*tag) {

    case 'a':
        if (! strcmp (tag, "array"))
            fn = end_array;
        break;

    case 'b':
        if (! strcmp (tag, "boolean"))
            fn = end_boolean;
        else if (! strcmp (tag, "base64"))
            fn = end_base64;
        break;

    case 'd':
        if (! strcmp (tag, "double"))
            fn = end_double;
        break;

    case 'f':
        if (! strcmp (tag, "fault"))
            fn = end_fault;
        break;

    case 'i':
        if (! strcmp (tag, "i4") || ! strcmp (tag, "int"))
            fn = end_int;
        break;

    case 'n':
        if (! strcmp (tag, "name"))
            fn = end_string;
        break;

    case 'p':
        if (! strcmp (tag, "params"))
            fn = end_params;
        break;

    case 's':
        if (! strcmp (tag, "string"))
            fn = end_string;
        else if (! strcmp (tag, "struct"))
            fn = end_struct;
        break;

    case 'v':
        if (! strcmp (tag, "value"))
            fn = end_value;
        break;
    }

    if (fn)
        fn (unm, data_str);

    Py_INCREF (Py_None);
    return Py_None;
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

    unm->flavor = PY_UNMARSHALLER_FLAVOR_NONE;
    unm->stack = g_ptr_array_new ();
    unm->marks = NULL;
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
    int i;

    for (i = 0; i < unm->stack->len; ++i) {
        PyObject *obj = g_ptr_array_index (unm->stack, i);
        Py_DECREF (obj);
    }
    g_ptr_array_free (unm->stack, TRUE);

    g_slist_free (unm->marks);
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
    { "xml",   unmarshaller_xml,   METH_VARARGS, "xml" },

    { "start", unmarshaller_start, METH_VARARGS, "start" },
    { "data",  unmarshaller_data,  METH_VARARGS, "data" },
    { "end",   unmarshaller_end,   METH_VARARGS, "end" },
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
}
